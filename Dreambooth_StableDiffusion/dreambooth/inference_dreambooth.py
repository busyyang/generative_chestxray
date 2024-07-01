from diffusers import StableDiffusionPipeline
import torch,os

save_dir = 'outputs/sampled_images'
if not os.path.exists(save_dir):
    os.makedirs(save_dir)

pipe = StableDiffusionPipeline.from_pretrained('outputs', torch_dtype = torch.float16).to('cuda')
prompt = 'a x-ray image of carm_vertebrae'

for i in range(100):
    images = pipe(prompt, num_inference_steps=150).images
    images[0].save(f'{save_dir}/{i}.png')