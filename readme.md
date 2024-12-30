---
license: apache-2.0  
language:  
- en  
base_model:  
- KwaiVGI/LivePortrait  
pipeline_tag: image-to-video 
library_name: "onnx,pytorch"

tags:  
- animation  
- imagetoanimation  
- faceanimation  
- bodyanimation  
- liveportrait  
---

# LivePortrait: Efficient Portrait Animation with Stitching and Retargeting Control

This is a replica of the official Space for the paper: [**LivePortrait: Efficient Portrait Animation with Stitching and Retargeting Control**](https://arxiv.org/abs/2407.03168).

## How to Use This Model

You can use this model to animate a portrait image by following the steps below:

### Requirements

Ensure you have `flask` and `pyngrok` installed, and the model repository cloned. You can also set up the environment and run the code on Google Colab for easy access.

### Running the Model on Google Colab

1. Install required packages:
    ```bash
    !pip install flask pyngrok
    ```

2. Clone the repository:
    ```bash
    !git clone https://huggingface.co/codewithRiz/image-2-animation
    ```

3. Install the required dependencies:
    ```bash
    !pip install -r /content/image-2-animation/requirements.txt
    ```

4. Set up the authentication token for Ngrok:
    ```python
    from pyngrok import ngrok
    ngrok.set_auth_token("YOUR_NGROK_AUTH_TOKEN")
    ```

5. Initialize the model handler:
    ```python
    import sys
    sys.path.append('/content/image-2-animation')
    from handler import EndpointHandler

    handler = EndpointHandler()
    ```

6. Upload the source image and driving video:
    ```python
    from google.colab import files
    uploaded_files = files.upload()  # This opens a file upload dialog

    source_image = None
    driving_video = None

    for filename in uploaded_files.keys():
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            source_image = filename
        elif filename.lower().endswith(('.mp4', '.avi')):
            driving_video = filename

    # Ensure both the image and video are uploaded
    if not source_image:
        print("Please upload a valid source image (jpg, png).")
        sys.exit(1)

    if not driving_video:
        print("Please upload a valid driving video (mp4, avi).")
        sys.exit(1)
    ```

7. Define input data for inference and run the model:
    ```python
    payload = {
        "source": source_image,  # Uploaded source image
        "driving": driving_video  # Uploaded driving video
    }

    response = handler(payload)

    if 'output_path' in response:
        output_path = response['output_path']
        print(f"Inference completed. Output saved at: {output_path}")
        
        # Download the output video
        files.download(output_path)  # Download the file to the user's machine
    else:
        print(response)
    ```

### Inference Details

- Upload a source image (jpg, png) and a driving video (mp4, avi).
- The model will generate an animated video using the input image and driving video.
- The output will be saved, and you can download it directly from the Colab interface.
