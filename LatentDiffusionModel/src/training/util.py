"""Utility functions for training."""
from pathlib import Path
from typing import Tuple, Union

import matplotlib.pyplot as plt
import mlflow.pytorch
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from custom_transforms import ApplyTokenizerd, LoadJSONd, RandomSelectExcerptd
from mlflow import start_run
from monai import transforms
from monai.data import PersistentDataset
from omegaconf import OmegaConf
from omegaconf.dictconfig import DictConfig
from tensorboardX import SummaryWriter
from torch.utils.data import DataLoader
from tqdm import tqdm
import json,os
from datetime import datetime 


def get_iu_datalist(dataset_path:str):
    with open(os.path.join(dataset_path, 'annotation.json'), "r") as f:
        data = json.load(f)
    train_data = []
    val_data = []
    for t in data['train']:
        train_data.append({
            'image': os.path.join(dataset_path, 'images', t['image_path'][0]),
            'report': [t['report']]
        })
    
    for t in data['val']:
        val_data.append({
            'image': os.path.join(dataset_path, 'images', t['image_path'][0]),
            'report': [t['report']]
        })
    
    return train_data, val_data

# ----------------------------------------------------------------------------------------------------------------------
# DATA LOADING
# ----------------------------------------------------------------------------------------------------------------------
def get_datalist(
    ids_path: str,
    extended_report: bool = False,
):
    """Get data dicts for data loaders."""
    df = pd.read_csv(ids_path, sep="\t")

    data_dicts = []
    for index, row in df.iterrows():
        report_path = row["report"]
        if extended_report:
            report_path = report_path.replace("report_sentences", "report_sentences_extended")
        data_dicts.append(
            {
                "image": f"{row['image']}",
                "report": report_path,
            }
        )

    print(f"Found {len(data_dicts)} subjects.")
    return data_dicts


def get_dataloader(
    cache_dir: Union[str, Path],
    batch_size: int,
    dataset_path: str,
    num_workers: int = 8,
    model_type: str = "autoencoder"
):
    # Define transformations
    val_transforms = transforms.Compose(
        [
            transforms.LoadImaged(keys=["image"]),
            transforms.EnsureChannelFirstd(keys=["image"]),
            transforms.Lambdad(
                keys=["image"],
                func=lambda x: x[0, :, :][
                    None,
                ],
            ),
            transforms.Resized(keys=["image"], spatial_size=(512, 512)),
            transforms.Rotate90d(keys=["image"], k=-1, spatial_axes=(0, 1)),  # Fix flipped image read
            transforms.Flipd(keys=["image"], spatial_axis=1),  # Fix flipped image read
            transforms.ScaleIntensityRanged(keys=["image"], a_min=0.0, a_max=255.0, b_min=0.0, b_max=1.0, clip=True),
            #transforms.CenterSpatialCropd(keys=["image"], roi_size=(512, 512)),
            transforms.RandAffined(
                    keys=["image"],
                    rotate_range=(0, 0),
                    translate_range=(-0, 0),
                    scale_range=(0, 0),
                    spatial_size=[512, 512],
                    prob=1,
                ),
            transforms.ToTensord(keys=["image"]),
            #LoadJSONd(keys=["report"]),
            #RandomSelectExcerptd(keys=["report"], sentence_key="sentences", max_n_sentences=5),
            ApplyTokenizerd(keys=["report"])
        ]
    )
    if model_type == "autoencoder":
        train_transforms = transforms.Compose(
            [
                transforms.LoadImaged(keys=["image"]),
                transforms.EnsureChannelFirstd(keys=["image"]),
                transforms.Lambdad(
                    keys=["image"],
                    func=lambda x: x[0, :, :][
                        None,
                    ],
                ),
                transforms.Resized(keys=["image"], spatial_size=(512, 512)),
                transforms.Rotate90d(keys=["image"], k=-1, spatial_axes=(0, 1)),  # Fix flipped image read
                transforms.Flipd(keys=["image"], spatial_axis=1),  # Fix flipped image read
                transforms.ScaleIntensityRanged(
                    keys=["image"], a_min=0.0, a_max=255.0, b_min=0.0, b_max=1.0, clip=True
                ),
                #transforms.CenterSpatialCropd(keys=["image"], roi_size=(512, 512)),
                transforms.RandAffined(
                    keys=["image"],
                    rotate_range=(-np.pi / 36, np.pi / 36),
                    translate_range=(-2, 2),
                    scale_range=(-0.01, 0.01),
                    spatial_size=[512, 512],
                    prob=0.5,
                ),
                transforms.RandFlipd(keys=["image"], spatial_axis=1, prob=0.5),
                transforms.ToTensord(keys=["image"]),
                #LoadJSONd(keys=["report"]),
                #RandomSelectExcerptd(keys=["report"], sentence_key="sentences", max_n_sentences=5),
                ApplyTokenizerd(keys=["report"])
            ]
        )
    if model_type == "diffusion":
        train_transforms = transforms.Compose(
            [
                transforms.LoadImaged(keys=["image"]),
                transforms.EnsureChannelFirstd(keys=["image"]),
                transforms.Lambdad(
                    keys=["image"],
                    func=lambda x: x[0, :, :][
                        None,
                    ],
                ),
                transforms.Resized(keys=["image"], spatial_size=(512, 512)),
                transforms.Rotate90d(keys=["image"], k=-1, spatial_axes=(0, 1)),  # Fix flipped image read
                transforms.Flipd(keys=["image"], spatial_axis=1),  # Fix flipped image read
                transforms.ScaleIntensityRanged(
                    keys=["image"], a_min=0.0, a_max=255.0, b_min=0.0, b_max=1.0, clip=True
                ),
                transforms.CenterSpatialCropd(keys=["image"], roi_size=(512, 512)),
                transforms.RandAffined(
                    keys=["image"],
                    rotate_range=(-np.pi / 36, np.pi / 36),
                    translate_range=(-2, 2),
                    scale_range=(-0.01, 0.01),
                    spatial_size=[512, 512],
                    prob=0.10,
                ),
                transforms.ToTensord(keys=["image"]),
                #LoadJSONd(keys=["report"]),
                #RandomSelectExcerptd(keys=["report"], sentence_key="sentences", max_n_sentences=5),
                ApplyTokenizerd(keys=["report"]),
                transforms.RandLambdad(
                    keys=["report"],
                    prob=0.10,
                    func=lambda x: torch.cat(
                        (49406 * torch.ones(1, 1), 49407 * torch.ones(1, x.shape[1] - 1)), 1
                    ).long(),
                ),  # 49406: BOS token 49407: PAD token
            ]
        )

    train_dicts,val_dicts = get_iu_datalist(dataset_path)
    train_ds = PersistentDataset(data=train_dicts, transform=train_transforms, cache_dir=str(cache_dir))
    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        drop_last=False,
        pin_memory=False,
        persistent_workers=True,
    )

    # val_dicts = get_datalist(ids_path=validation_ids, extended_report=extended_report)
    val_ds = PersistentDataset(data=val_dicts, transform=val_transforms, cache_dir=str(cache_dir))
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        num_workers=num_workers,
        drop_last=False,
        pin_memory=False,
        persistent_workers=True,
    )

    return train_loader, val_loader


# ----------------------------------------------------------------------------------------------------------------------
# LOGS
# ----------------------------------------------------------------------------------------------------------------------
def recursive_items(dictionary, prefix=""):
    for key, value in dictionary.items():
        if type(value) in [dict, DictConfig]:
            yield from recursive_items(value, prefix=str(key) if prefix == "" else f"{prefix}.{str(key)}")
        else:
            yield (str(key) if prefix == "" else f"{prefix}.{str(key)}", value)


def log_mlflow(
    model,
    config,
    args,
    experiment: str,
    run_dir: Path,
    val_loss: float,
):
    """Log model and performance on Mlflow system"""
    config = {**OmegaConf.to_container(config), **vars(args)}
    print(f"Setting mlflow experiment: {experiment}")
    mlflow.set_experiment(experiment)


    with start_run():
        print(f"MLFLOW URI: {mlflow.tracking.get_tracking_uri()}")
        print(f"MLFLOW ARTIFACT URI: {mlflow.get_artifact_uri()}")

        for key, value in recursive_items(config):
            mlflow.log_param(key, str(value))

        mlflow.log_artifacts(str(run_dir / "train"), artifact_path="events_train")
        mlflow.log_artifacts(str(run_dir / "val"), artifact_path="events_val")
        mlflow.log_metric(f"loss", val_loss, 0)

        raw_model = model.module if hasattr(model, "module") else model
        mlflow.pytorch.log_model(raw_model, "final_model")


def get_figure(
    img: torch.Tensor,
    recons: torch.Tensor,
):
    
    pairs = []
    for i in range(img.shape[0]):
        input_ = np.clip(a=img[i, 0, :, :].cpu().numpy(), a_min=0, a_max=1)
        recon_ = np.clip(a=recons[i, 0, :, :].cpu().numpy(), a_min=0, a_max=1)
        pairs.append(np.concatenate((input_, recon_), axis=0))
    
    f = np.concatenate(pairs, axis=1)

    fig = plt.figure(dpi=300)
    plt.imshow(f, cmap="gray")
    plt.axis("off")
    return fig


def log_reconstructions(
    image: torch.Tensor,
    reconstruction: torch.Tensor,
    writer: SummaryWriter,
    step: int,
    title: str = "RECONSTRUCTION"
) -> None:
    fig = get_figure(
        image,
        reconstruction,
    )
    fig.savefig(os.path.join(writer.logdir, f"{title}_{step}.png"), bbox_inches="tight")
    writer.add_figure(title, fig, step)


@torch.no_grad()
def log_ldm_sample_unconditioned(
    model: nn.Module,
    stage1: nn.Module,
    text_encoder,
    scheduler: nn.Module,
    spatial_shape: Tuple,
    writer: SummaryWriter,
    step: int,
    device: torch.device,
    scale_factor: float = 1.0,
) -> None:
    latent = torch.randn((1,) + spatial_shape)
    latent = latent.to(device)

    prompt_embeds = torch.cat((49406 * torch.ones(1, 1), 49407 * torch.ones(1, 76)), 1).long().to(device)
    prompt_embeds = text_encoder(prompt_embeds.squeeze(1))
    prompt_embeds = prompt_embeds[0]

    for t in tqdm(scheduler.timesteps, ncols=70,desc='Sample Image:'):
        noise_pred = model(x=latent, timesteps=torch.asarray((t,)).to(device), context=prompt_embeds)
        latent, _ = scheduler.step(noise_pred, t, latent)

    x_hat = stage1.model.decode(latent / scale_factor)
    img_0 = np.clip(a=x_hat[0, 0, :, :].cpu().numpy(), a_min=0, a_max=1)
    fig = plt.figure(dpi=300)
    plt.imshow(img_0, cmap="gray")
    plt.axis("off")
    writer.add_figure("SAMPLE", fig, step)
  
def generate_folder_from_current_time(prefix:str=''):  
    current_time = datetime.now()   
    formatted_time = current_time.strftime('%Y-%m-%d_%H-%M-%S')  
    folder_path = os.path.join(prefix, formatted_time)
    if not os.path.exists(folder_path):  
        os.makedirs(folder_path)
    return folder_path