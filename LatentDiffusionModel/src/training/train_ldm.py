""" Training script for the diffusion model in the latent space of the pretraine AEKL model. """
import argparse
import warnings
from pathlib import Path

import mlflow.pytorch
import torch
import torch.nn as nn
import torch.optim as optim
from generative.networks.nets import DiffusionModelUNet
from generative.networks.schedulers import DDPMScheduler
from monai.config import print_config
from monai.utils import set_determinism
from omegaconf import OmegaConf
from tensorboardX import SummaryWriter
from training_functions import train_ldm
from transformers import CLIPTextModel
from util import get_dataloader, log_mlflow

warnings.filterwarnings("ignore")


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--seed", type=int, default=2, help="Random seed to use.")
    parser.add_argument("--run_dir", default="LDM", help="Location of model to resume.")
    parser.add_argument("--dataset_path",default='datasets/XrayGenerationDataset', help="Location of training set.")
    parser.add_argument("--config_file",default='configs/ldm/ldm_v0.yaml', help="Location of ldm configuration file.")
    parser.add_argument("--stage1_uri",default='mlruns/149355113917878320/d2ec6c4c9fc044c5851f0a59aee7026c/artifacts/final_model', help="Path readable by load_model.")
    parser.add_argument("--scale_factor", type=float, default=0.3, help="signal-to-noise ratio.")
    parser.add_argument("--batch_size", type=int, default=16, help="Training batch size.")
    parser.add_argument("--n_epochs", type=int, default=500, help="Number of epochs to train.")
    parser.add_argument("--eval_freq", type=int, default=10, help="Number of epochs to between evaluations.")
    parser.add_argument("--num_workers", type=int, default=8, help="Number of loader workers")
    parser.add_argument("--extended_report", type=int, default=1, help="Define if use extended reports (only valid MIMIC-CXR dataset.)")
    parser.add_argument("--experiment", default='AE_KL', help="Mlflow experiment name.")

    args = parser.parse_args()
    return args


class Stage1Wrapper(nn.Module):
    """Wrapper for stage 1 model as a workaround for the DataParallel usage in the training loop."""

    def __init__(self, model: nn.Module) -> None:
        super().__init__()
        self.model = model

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z_mu, z_sigma = self.model.encode(x)
        z = self.model.sampling(z_mu, z_sigma)
        return z


def main(args):
    set_determinism(seed=args.seed)
    print_config()

    output_dir = Path("runs/")
    output_dir.mkdir(exist_ok=True, parents=True)

    run_dir = output_dir / args.run_dir
    if run_dir.exists() and (run_dir / "checkpoint.pth").exists():
        resume = True
    else:
        resume = False
        run_dir.mkdir(exist_ok=True)

    print(f"Run directory: {str(run_dir)}")
    print(f"Arguments: {str(args)}")
    for k, v in vars(args).items():
        print(f"  {k}: {v}")

    writer_train = SummaryWriter(log_dir=str(run_dir / "train"))
    writer_val = SummaryWriter(log_dir=str(run_dir / "val"))

    print("Getting data...")
    cache_dir = output_dir / "cached_data_diffusion"
    cache_dir.mkdir(exist_ok=True)

    train_loader, val_loader = get_dataloader(
        cache_dir=cache_dir,
        batch_size=args.batch_size,
        dataset_path=args.dataset_path,
        num_workers=args.num_workers,
        model_type="diffusion"
    )

    # Load Autoencoder to produce the latent representations
    print(f"Loading Stage 1 from {args.stage1_uri}")
    stage1 = mlflow.pytorch.load_model(args.stage1_uri)
    stage1 = Stage1Wrapper(model=stage1)
    stage1.eval()

    # Create the diffusion model
    print("Creating model...")
    config = OmegaConf.load(args.config_file)
    diffusion = DiffusionModelUNet(**config["ldm"].get("params", dict()))
    scheduler = DDPMScheduler(**config["ldm"].get("scheduler", dict()))

    text_encoder = CLIPTextModel.from_pretrained("stabilityai/stable-diffusion-2-1-base", subfolder="text_encoder")

    print(f"Let's use {torch.cuda.device_count()} GPUs!")
    device = torch.device("cuda")
    if torch.cuda.device_count() > 1:
        stage1 = torch.nn.DataParallel(stage1)
        diffusion = torch.nn.DataParallel(diffusion)
        text_encoder = torch.nn.DataParallel(text_encoder)

    stage1 = stage1.to(device)
    diffusion = diffusion.to(device)
    text_encoder = text_encoder.to(device)

    optimizer = optim.AdamW(diffusion.parameters(), lr=config["ldm"]["base_lr"])
    lr_scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, args.n_epochs, eta_min=1e-7, last_epoch=-1, verbose=False)
    # Get Checkpoint
    best_loss = float("inf")
    start_epoch = 0
    if resume:
        print(f"Using checkpoint!")
        checkpoint = torch.load(str(run_dir / "checkpoint.pth"))
        diffusion.load_state_dict(checkpoint["diffusion"])
        # Issue loading optimizer https://github.com/pytorch/pytorch/issues/2830
        optimizer.load_state_dict(checkpoint["optimizer"])
        start_epoch = checkpoint["epoch"]
        best_loss = checkpoint["best_loss"]
    else:
        print(f"No checkpoint found.")

    # Train model
    print(f"Starting Training")
    val_loss = train_ldm(
        model=diffusion,
        stage1=stage1,
        scheduler=scheduler,
        text_encoder=text_encoder,
        start_epoch=start_epoch,
        best_loss=best_loss,
        train_loader=train_loader,
        val_loader=val_loader,
        optimizer=optimizer,
        lr_scheduler=lr_scheduler,
        n_epochs=args.n_epochs,
        eval_freq=args.eval_freq,
        writer_train=writer_train,
        writer_val=writer_val,
        device=device,
        run_dir=run_dir,
        scale_factor=args.scale_factor,
    )

    log_mlflow(
        model=diffusion,
        config=config,
        args=args,
        experiment=args.experiment,
        run_dir=run_dir,
        val_loss=val_loss,
    )


if __name__ == "__main__":
    args = parse_args()
    main(args)
