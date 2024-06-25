"""
Create a dataset from C-arm images. There are two part of images:
 - Xray_loc/MergeLoc: images are in nifti format and we could know the name of each vertebra.
 - obb_detection/c-arm_data: images are in png/bmp format but we could not know the name of each vertebra.

In this script, we format a dataset to train a xray image generation model by LDM or related.

The test information should be:
This is an X-ray image taken by a C-arm, covering num vertebrae, namely L1, L2, L3 and L4.
This is an X-ray image taken by a C-arm. It includes num vertebrae, but the specific names of the vertebrae are unclear.
"""


import os,json
from tqdm import tqdm
from glob import glob
import shutil

SAVE_PATH = "/datastore2/yangjie/XrayGenerationDataset"
XRAY_PATH = "/home/jirui/yangjie/remote_a100_share/repos/MaestroAlgoXrayImageDetection/00.datasets"

def name_string(vertebrae:list):
    v_dict = {
        1: 'C1', 2: 'C2', 3: 'C3', 4: 'C4', 5: 'C5', 6: 'C6', 7: 'C7',
        8: 'T1', 9: 'T2', 10: 'T3', 11: 'T4', 12: 'T5', 13: 'T6', 14: 'T7',
        15: 'T8', 16: 'T9', 17: 'T10', 18: 'T11', 19: 'T12',
        20: 'L1', 21: 'L2', 22: 'L3', 23: 'L4', 24: 'L5', 25: 'L6', 26: 'Sacrum'
    }
    if len(vertebrae) == 1:
        return v_dict[vertebrae[0]]
    elif len(vertebrae) == 2:
        return f'{v_dict[vertebrae[0]]} and {v_dict[vertebrae[1]]}'
    else:
        name_str =''
        for i in range(len(vertebrae)-2):
            name_str += f'{v_dict[vertebrae[i]]}, '
        name_str += f'{v_dict[vertebrae[-2]]} and {v_dict[vertebrae[-1]]}'
        return name_str

def format_xrayimage_with_name(root:str, dataset:dict={}):
    images = glob(root+'/images/*.nii.gz')
    for image in tqdm(images,desc='Format XrayImage with name'):
        image_id = os.path.basename(image)[:-7]
        json_path = root +'/jsons/'+image_id+'.json'
        with open(json_path,'r') as f:
            json_data = json.load(f)
        vertebrae = [i['verte'] for i in json_data]
        vertebrae = sorted(vertebrae)
        report = f'This is an X-ray image taken by a C-arm, covering {len(vertebrae)} vertebrae, namely {name_string(vertebrae)}.'
        dataset[image_id] = {
            'image_path':[os.path.basename(image)],
            'report':report,
        }
    return dataset


def format_xrayimage_without_name(root:str, dataset:dict={}):
    images = glob(root+'/images/*')
    for image in tqdm(images,desc='Format XrayImage without name'):
        image_id = os.path.basename(image)[:-4]
        if image_id in dataset.keys():
            #shutil.copy(image, SAVE_PATH+'/images/'+os.path.basename(image))
            dataset[image_id]['image_path'] = [os.path.basename(image)]
            continue
        txt_path = root +'/labelTxt/'+image_id+'.txt'
        with open(txt_path,'r') as f:
            txt_data = f.readlines()
        report = f'This is an X-ray image taken by a C-arm. It includes {len(txt_data)} vertebrae, but the specific names of the vertebrae are unclear.'
        dataset[image_id] = {
            'image_path':[os.path.basename(image)],
            'report':report
        }
        #shutil.copy(image, SAVE_PATH+'/images/'+os.path.basename(image))
    return dataset


if __name__ == "__main__":
    dataset = {}
    dataset = format_xrayimage_with_name(XRAY_PATH+'/Xray_loc/MergeLoc', dataset)
    dataset = format_xrayimage_without_name(XRAY_PATH+'/obb_detection_data/c-arm_data', dataset)
    print('Num of samples: ',len(dataset))


    save_data={
        'train':[],
        'val':[]
    }
    i = 1
    for k,v in dataset.items():
        if i% 10 == 0:
            save_data['val'].append(v)
        else:
            save_data['train'].append(v)
        i += 1
    
    with open(SAVE_PATH+'/annotation.json','w') as f:
        json.dump(save_data, f, indent=4)