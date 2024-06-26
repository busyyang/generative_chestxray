"""Utility functions for testing."""
from __future__ import annotations

import pandas as pd
from monai import transforms
from monai.data import CacheDataset
from torch.utils.data import DataLoader
import os,json


def get_test_dataloader(
    batch_size: int,
    dataset_path: str,
    num_workers: int = 8,
    upper_limit: int | None = None,
):
    test_transforms = transforms.Compose(
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
            transforms.ToTensord(keys=["image"]),
        ]
    )

    test_dicts = get_iu_datalist_test(dataset_path)
    test_ds = CacheDataset(data=test_dicts, transform=test_transforms)
    test_loader = DataLoader(
        test_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        drop_last=False,
        pin_memory=False,
        persistent_workers=True,
    )

    return test_loader

def get_iu_datalist_test(dataset_path:str):
    with open(os.path.join(dataset_path, 'annotation.json'), "r") as f:
        data = json.load(f)
    test_data = []
    for t in data['test']:
        test_data.append({
            'image': os.path.join(dataset_path, 'images', t['image_path'][0]),
            'report': [t['report']]
        })
    return test_data


def get_datalist(
    ids_path: str,
    upper_limit: int | None = None,
):
    """Get data dicts for data loaders."""
    df = pd.read_csv(ids_path, sep="\t")

    if upper_limit is not None:
        df = df[:upper_limit]

    data_dicts = []
    for index, row in df.iterrows():
        data_dicts.append(
            {
                "image": f"{row['image']}",
            }
        )

    print(f"Found {len(data_dicts)} subjects.")
    return data_dicts
