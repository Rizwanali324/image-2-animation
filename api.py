# new requrements
from flask import Flask, request, jsonify, send_file, send_from_directory
import json
from pyngrok import ngrok
import subprocess
import os
import glob
import werkzeug
import uuid  
from math import ceil
from flask_httpauth import HTTPBasicAuth
from flask import request
auth = HTTPBasicAuth()

# Set the auth token for ngrok
ngrok.set_auth_token("2oclGQq2wjj2QBvfFqKaxdk7iuQ_bD9mhRPSqovvrGZb5ZP9")

app = Flask(__name__)
auth = HTTPBasicAuth()
users = {
    "admin": "password123"  
}

@auth.verify_password
def verify_password(username, password):
    if username in users and users[username] == password:
        return username
    return None

ANIMATIONS_PATH = "./animations"
UPLOADS_PATH = "./uploads"

os.makedirs(ANIMATIONS_PATH, exist_ok=True)
os.makedirs(UPLOADS_PATH, exist_ok=True)

SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.webm','.pkl'}

server_available = True  
def is_valid_file(filename, valid_extensions):
    """ Check if the file has a valid extension """
    return any(filename.lower().endswith(ext) for ext in valid_extensions)


# Path to the JSON file where model_list data is saved
MODEL_LIST_PATH = 'model_list.json'


# Function to load model list from the JSON file
def load_model_list():
    print("Attempting to load model list from JSON...")
    if os.path.exists(MODEL_LIST_PATH):
        try:
            with open(MODEL_LIST_PATH, 'r') as f:
                model_list = json.load(f)
            print(f"Successfully loaded model list from {MODEL_LIST_PATH}")
            return model_list
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {MODEL_LIST_PATH}: {e}")
            return {}  # Return an empty dictionary if JSON is invalid
    else:
        print(f"Model list JSON file not found at {MODEL_LIST_PATH}")
        return {}  # Return an empty dictionary if the file doesn't exist

# Function to save model list to the JSON file
def save_model_list(model_list):
    print("Attempting to save model list to JSON...")
    try:
        with open(MODEL_LIST_PATH, 'w') as f:
            json.dump(model_list, f, indent=4)
        print(f"Successfully saved model list to {MODEL_LIST_PATH}")
    except Exception as e:
        print(f"Error saving model list to {MODEL_LIST_PATH}: {e}")




@app.route('/upload-video', methods=['POST'])
@auth.login_required
def upload_video():
    if not server_available:
        return jsonify({"error": "Service temporarily unavailable"}), 503
    video_files = request.files.getlist('videoFile')
    category = request.form.get('category')
    if not category:
        return jsonify({"error": "Category is required"}), 400
    if not video_files:
        return jsonify({"error": "No video files uploaded"}), 400
    category_folder_path = os.path.join(UPLOADS_PATH, category)
    os.makedirs(category_folder_path, exist_ok=True)
    model_list = load_model_list()
    if category not in model_list:
        model_list[category] = []
    uploaded_videos = []
    for video_file in video_files:
        if video_file.filename.endswith('.pkl'):
            pkl_filename = werkzeug.utils.secure_filename(video_file.filename)
            pkl_filepath = os.path.join(category_folder_path, pkl_filename)
            video_file.save(pkl_filepath)
            uploaded_videos.append(pkl_filename)
            continue
        if not is_valid_file(video_file.filename, SUPPORTED_VIDEO_EXTENSIONS):
            continue
        video_filename = werkzeug.utils.secure_filename(video_file.filename)
        video_filepath = os.path.join(category_folder_path, video_filename)
        existing_video = next((video for video in model_list[category] if video["videoUrl"] == video_filepath), None)
        if existing_video:
            video_file.save(video_filepath)
            existing_video["videoId"] = existing_video["videoId"]
        else:
            video_id = str(uuid.uuid4())
            model_list[category].append({
                "videoId": video_id,
                "videoUrl": video_filepath
            })
            video_file.save(video_filepath)
        uploaded_videos.append(video_filename)
    save_model_list(model_list)
    if uploaded_videos:
        return jsonify({
            "message": "Files uploaded successfully",
            "uploaded_files": uploaded_videos,
            "category": category
        }), 201
    else:
        return jsonify({
            "error": "No valid files were uploaded",
            "supported_formats": list(SUPPORTED_VIDEO_EXTENSIONS)
        }), 400


@app.route('/get-all-models', methods=['GET'])
@auth.login_required
def get_all_models():
    """Retrieves paginated video models for a specific category with full URLs and validation"""
    model_list = load_model_list()  
    base_url = request.host_url  
    category = request.args.get('category')  
    page = request.args.get('page', '1') 
    try:
        page = int(page)
        if page < 1:
            raise ValueError("Page number must be a positive integer.")
    except ValueError:
        return jsonify({"error": "Invalid page number. It must be a positive integer."}), 400
    if not category:
        if 'page' in request.args:
            return jsonify({
                "error": "Category is required when specifying a page.",
                "available_categories": list(model_list.keys())
            }), 400
        return jsonify({
            "available_categories": list(model_list.keys())
        }), 200
    if category not in model_list:
        return jsonify({
            "error": "Category not found",
            "available_categories": list(model_list.keys())  # Return available categories
        }), 404
    videos = model_list[category]
    total_items = len(videos)
    per_page = 5  
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_videos = videos[start_index:end_index]
    if not paginated_videos:
        return jsonify({"error": "Page not found"}), 404
    response = {
        "category": category,
        "videos": [
            {
                "videoId": video["videoId"],
                "videoUrl": base_url + video["videoUrl"].lstrip('/')  # Full URL for video
            }
            for video in paginated_videos
        ],
        "pagination": {
            "total_items": total_items,
            "total_pages": (total_items // per_page) + (1 if total_items % per_page > 0 else 0),
            "current_page": page,
            "has_next": end_index < total_items,
            "has_prev": start_index > 0
        }
    }
    return jsonify(response), 200




@app.route('/delete-video', methods=['DELETE'])
@auth.login_required
def delete_video():
    """Deletes a specified video from its category and updates the JSON model list."""
    
    category = request.args.get('category')
    video_path = request.args.get('path')
    model_list = load_model_list()
    available_categories = list(model_list.keys()) 
    if not category and not video_path:
        return jsonify({
            "error": "Either category or video path is required",
            "available_categories": available_categories
        }), 400

    # Replace "\\" and "/" in the video path with the correct platform separator
    if video_path:
        video_path = video_path.replace("\\", os.sep).replace("/", os.sep)
    if category:
        print(f"Attempting to delete category: {category}")
        
        if category in model_list:
            for video in model_list[category]:
                try:
                    video_path_in_model = video["videoUrl"].replace("\\", os.sep).replace("/", os.sep)
                    print(f"Deleting video file: {video_path_in_model}")
                    os.remove(video_path_in_model)
                    print(f"Deleted video file: {video_path_in_model}")
                    # Check for corresponding .pkl file in the same folder
                    pkl_file_path = os.path.splitext(video_path_in_model)[0] + '.pkl'
                    if os.path.exists(pkl_file_path):
                        os.remove(pkl_file_path)
                        print(f"Deleted pkl file: {pkl_file_path}")
                
                except FileNotFoundError:
                    print(f"Video file not found: {video_path_in_model}")

            del model_list[category]
            print(f"Deleted category: {category}")

            # Delete the category folder on disk if it exists
            category_folder_path = os.path.join(UPLOADS_PATH, category)
            if os.path.exists(category_folder_path):
                os.rmdir(category_folder_path)
                print(f"Deleted category folder: {category_folder_path}")

            save_model_list(model_list)

            return jsonify({"message": f"Category '{category}' and all its videos deleted successfully"}), 200
        else:
            print(f"Category '{category}' not found in model list.")
            return jsonify({
                "error": f"Category '{category}' not found",
                "available_categories": available_categories
            }), 404

    # If only a video path is provided, delete the specific video
    if video_path:
        print(f"Attempting to delete video at path: {video_path}")
        video_found_in_models = False
        category_to_update = None

        for category, videos in model_list.items():
            for video in videos:
                video_path_in_model = video["videoUrl"].replace("\\", os.sep).replace("/", os.sep)
                if video_path_in_model == video_path:
                    videos.remove(video)
                    video_found_in_models = True
                    category_to_update = category
                    print(f"Found video in category: {category}")
                    break
            if video_found_in_models:
                if not model_list[category]:
                    del model_list[category]
                    print(f"Deleted empty category: {category}")
                break

        if video_found_in_models:
            try:
                print(f"Deleting video file: {video_path}")
                os.remove(video_path)
                print(f"Deleted video: {video_path}")
                
                # Delete the corresponding .pkl file in the same folder
                pkl_file_path = os.path.splitext(video_path)[0] + '.pkl'
                if os.path.exists(pkl_file_path):
                    os.remove(pkl_file_path)
                    print(f"Deleted pkl file: {pkl_file_path}")

                save_model_list(model_list)
                
                return jsonify({"message": f"Video deleted successfully from category '{category_to_update}' and JSON updated"}), 200
            except FileNotFoundError:
                print(f"Video file not found on disk: {video_path}")
                return jsonify({"error": "Video file not found on disk"}), 404

        if os.path.exists(video_path):
            os.remove(video_path)  
            print(f"Video {video_path} deleted successfully from disk but not in model list.")
            
            # Delete the corresponding .pkl file if it exists
            pkl_file_path = os.path.splitext(video_path)[0] + '.pkl'
            if os.path.exists(pkl_file_path):
                os.remove(pkl_file_path)
                print(f"Deleted pkl file: {pkl_file_path}")

            save_model_list(model_list)
            return jsonify({"message": f"Video deleted successfully from disk but not in model list."}), 200

        print(f"Video not found in model list or disk: {video_path}")
        return jsonify({"error": "Video not found. Check category name or video path."}), 404

@app.route('/inference', methods=['POST'])
@auth.login_required
def run_inference():
    global server_available

    # Check if the server is available
    if not server_available:
        return jsonify({"error": "Service temporarily unavailable"}), 503

    # Get the uploaded source image
    source_images = request.files.getlist('source_image')

    # Validate the uploaded source image file
    if len(source_images) != 1:
        return jsonify({"error": "Please upload exactly one source image file"}), 400

    source_image_file = source_images[0]

    if not is_valid_file(source_image_file.filename, SUPPORTED_IMAGE_EXTENSIONS):
        return jsonify({
            "error": "Invalid file format for source image",
            "supported_formats": list(SUPPORTED_IMAGE_EXTENSIONS)
        }), 400

    # Check for an optional videoId or uploaded driving video file
    video_id = request.form.get('videoId')
    driving_video_file = request.files.get('driving_video')

    driving_video_path = None
    pkl_file_path = None  # Initialize the pkl_file_path to avoid reference before assignment

    # If videoId is provided, retrieve the corresponding video path
    if video_id:
        print(f"Video ID provided: {video_id}")
        
        # Search for the video in the model_list
        model_list = load_model_list()

        # Iterate through the model list and check if the videoId matches
        for category, videos in model_list.items():
            for video in videos:
                if video["videoId"] == video_id:
                    # Extract base name of the video URL (without extension)
                    video_base_name = os.path.splitext(os.path.basename(video["videoUrl"]))[0]

                    # Construct the pkl file path based on the video base name
                    pkl_file_path = os.path.join(UPLOADS_PATH, "demo", f"{video_base_name}.pkl")

                    # Debug print for checking if pkl file exists
                    if os.path.exists(pkl_file_path):
                        print(f"Using .pkl file: {pkl_file_path}")
                        driving_video_path = pkl_file_path  # Use the .pkl file if it exists
                    else:
                        print(f".pkl file does not exist, using video URL: {video['videoUrl']}")
                        # If the .pkl file doesn't exist, use the video URL
                        driving_video_path = video["videoUrl"]
                    break
            if driving_video_path:
                break

        if not driving_video_path:
            return jsonify({"error": "Invalid videoId. Video not found."}), 404

    else:
        # Validate the uploaded driving video file if videoId is not provided
        if not driving_video_file:
            return jsonify({"error": "Please upload exactly one driving video file or provide videoId."}), 400

        # Check if the user uploaded more than one driving video
        if len(request.files.getlist('driving_video')) > 1:
            return jsonify({"error": "Please upload exactly one driving video file"}), 400

        # Validate the uploaded driving video file
        if not is_valid_file(driving_video_file.filename, SUPPORTED_VIDEO_EXTENSIONS):
            return jsonify({
                "error": "Invalid file format for driving video",
                "supported_formats": list(SUPPORTED_VIDEO_EXTENSIONS)
            }), 400

        # Save the uploaded driving video file
        driving_video_path = os.path.join(UPLOADS_PATH, werkzeug.utils.secure_filename(driving_video_file.filename))
        driving_video_file.save(driving_video_path)

    # Save the uploaded source image file
    source_image_path = os.path.join(UPLOADS_PATH, werkzeug.utils.secure_filename(source_image_file.filename))
    source_image_file.save(source_image_path)

    # Construct initial and short output filenames
    source_initial = os.path.basename(source_image_path)[0]
    driving_initial = os.path.basename(driving_video_path)[0]
    short_output_filename = f"{source_initial}_{driving_initial}.mp4"
    short_output_filepath = os.path.join(ANIMATIONS_PATH, short_output_filename)

    try:
        # Run the inference command
        command = ['python', './inference.py', '-s', source_image_path, '-d', driving_video_path, '--flag_do_torch_compile']
        subprocess.run(command, check=True, cwd='.')

        # Locate the full output file path by listing files in the animations folder
        full_output_filepath = None
        for file in glob.glob(os.path.join(ANIMATIONS_PATH, "*.mp4")):
            if source_image_path.split('/')[-1].split('.')[0] in file and driving_video_path.split('/')[-1].split('.')[0] in file:
                full_output_filepath = file
                break

        # Check if the output file was created
        if not full_output_filepath or not os.path.exists(full_output_filepath):
            return jsonify({"error": f"Output video not found at {full_output_filepath}"}), 500

        # Rename to the shorter output filename
        os.rename(full_output_filepath, short_output_filepath)

        # Clean up .pkl files
        pkl_files = glob.glob("./uploads/*.pkl")
        for pkl_file in pkl_files:
            os.remove(pkl_file)
            print(f"Removed pkl file: {pkl_file}")

        # Return the output file with the short filename
        return send_file(short_output_filepath, as_attachment=True)

    except subprocess.CalledProcessError as e:
        return jsonify({"error": "An error occurred while generating the animation"}), 500
    except FileNotFoundError as fnfe:
        return jsonify({"error": f"File not found: {str(fnfe)}"}), 500
    except Exception as ex:
        return jsonify({"error": f"Unexpected error: {str(ex)}"}), 500
    finally:
        # Delete uploaded input files after inference
        try:
            os.remove(source_image_path)
            # Clean up the driving video file only if uploaded (not when using pre-uploaded)
            if not video_id:
                os.remove(driving_video_path)
        except Exception as e:
            print(f"Error cleaning up files: {str(e)}")




@app.route('/uploads/<path:filename>')
def serve_file(filename):
    return send_from_directory('uploads', filename)

@app.route('/clear-animations', methods=['POST'])
@auth.login_required
def clear_animations():
    global server_available
    if not server_available:
        return jsonify({"error": "Service temporarily unavailable"}), 503
    try:
        animation_files = glob.glob(os.path.join(ANIMATIONS_PATH, "*"))
        if not animation_files:
            return jsonify({"message": "No animation files to delete"}), 200
        for file_path in animation_files:
            os.remove(file_path)
            print(f"Deleted: {file_path}")
        return jsonify({"message": "All animation files deleted successfully"}), 200
    except Exception as ex:
        return jsonify({"error": f"Failed to clear animations: {str(ex)}"}), 500
    
    
@app.errorhandler(503)
def service_unavailable(e):
    return jsonify({"error": "Service temporarily unavailable"}), 503

if __name__ == '__main__':
    public_url = ngrok.connect(5000)
    print("Public URL:", public_url)
    app.run(host='0.0.0.0')