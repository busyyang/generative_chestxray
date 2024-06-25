# Latent Diffusion Models for Chest X-Ray Generation using MONAI Generative Models

Script to train a Latent Diffusion Model based on [Pinaya et al. "Brain imaging generation with latent diffusion models.
"](https://arxiv.org/abs/2209.07162) on the MIMIC-CXR dataset using [MONAI Generative Models
](https://github.com/Project-MONAI/GenerativeModels) package.


## 数据集

由于训练LDM模型需要数据有文本信息输入，在推理的时候用于conditional的生成，这里的数据采用C-arm的X光图像数据。对于标注了椎体名称的数据，对应的文本信息为：
~~~
'This is an X-ray image taken by a C-arm, covering {4} vertebrae, namely {L1, L2, L3, L4 and L5}.'
~~~
对应的椎体数量和椎体名称按实际情况替换。 对于仅标注了椎体但是较难识别椎体名称的数据，对应的文本信息为：
~~~
'This is an X-ray image taken by a C-arm. It includes {4} vertebrae, but the specific names of the vertebrae are unclear.'
~~~

图像与标注属于来源于`MaestroAlgoXrayImageDetection`项目的`00.datasets`目录，使用`src/preprocessing/create_carm_dataset.py`生成数据集。
生成的数据集包含一个`images`文件夹和一个`annotation.json`文件。在运行`src/preprocessing/create_carm_dataset.py`之前检查相关路径是否正确/有效。

由于3090服务器的`/home`文件夹空间有限，建议将数据放在`/datastore2`下（SSD），并设置软连接映射到`datasets`文件夹下，如：
~~~
ln -rs /datastore2/yangjie/XrayGenerationDataset ~/yangjie/repos/generative_chestxray/datasets/
~~~

## 训练

## 采样

## 性能分析


## 环境
参考`requirements.txt`, 或：
~~~
conda activate monai
~~~

## Reference
1. Step by Step搭建本仓代码：https://towardsdatascience.com/generating-medical-images-with-monai-e03310aa35e6
2. 代码来源：https://github.com/Warvito/generative_chestxray
3. https://zhuanlan.zhihu.com/p/618066889
4. Bilibili上一个讲AIGC比较清楚的视频：https://www.bilibili.com/video/BV1tY4y1Z7eR
5. https://huggingface.co/blog/annotated-diffusion