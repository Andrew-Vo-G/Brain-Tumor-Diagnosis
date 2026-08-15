import os
import numpy as np
import sys
import time
import threading
from PIL import Image

CLASSES = ['Glioma', 'Meningioma', 'No Tumor', 'Pituitary']
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")

# Fix for YOLO initialization hangs/internet reaching
os.environ["YOLO_OFFLINE"] = "True"
os.environ["YOLO_VERBOSE"] = "False"

# Lazy imports — these heavy libraries are imported only when needed
# to prevent uvicorn from hanging at startup on macOS
torch = None
cv2 = None
nn = None
F = None
transforms = None
models = None
YOLO = None
_import_lock = threading.Lock()
_imports_done = False

def _ensure_imports():
    """Import heavy ML libraries lazily on first use. Thread-safe."""
    global torch, cv2, nn, F, transforms, models, YOLO, _imports_done
    if _imports_done:
        return
    with _import_lock:
        if _imports_done:
            return
        import torch as _torch
        torch = _torch
        import cv2 as _cv2
        cv2 = _cv2
        import torch.nn as _nn
        nn = _nn
        import torch.nn.functional as _F
        F = _F
        from torchvision import transforms as _transforms, models as _models
        transforms = _transforms
        models = _models
        from ultralytics import YOLO as _YOLO
        YOLO = _YOLO
        _imports_done = True
        sys.stderr.write("Heavy ML libraries imported successfully\n")


class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        self.forward_handle = self.target_layer.register_forward_hook(self.save_activation)
        self.backward_handle = self.target_layer.register_full_backward_hook(self.save_gradient)

    def remove_hooks(self):
        self.forward_handle.remove()
        self.backward_handle.remove()

    def save_activation(self, module, input, output):
        self.activations = output.detach()

    def save_gradient(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def __call__(self, x, class_idx=None):
        self.model.eval()
        output = self.model(x)
        if class_idx is None:
            class_idx = torch.argmax(output, dim=1).item()
            
        self.model.zero_grad()
        target = output[:, class_idx]
        target.backward(retain_graph=True)
        
        gradients = self.gradients.cpu().data.numpy()[0]
        activations = self.activations.cpu().data.numpy()[0]
        weights = np.mean(gradients, axis=(1, 2))
        
        cam = np.zeros(activations.shape[1:], dtype=np.float32)
        for i, w in enumerate(weights):
            cam += w * activations[i]
            
        cam = np.maximum(cam, 0)
        cam = cv2.resize(cam, (x.shape[3], x.shape[2]))
        
        cam_min, cam_max = np.min(cam), np.max(cam)
        if cam_max - cam_min > 0:
            cam = (cam - cam_min) / (cam_max - cam_min)
        else:
            cam = np.zeros_like(cam)
            
        return cam

def apply_gradcam_overlay(img_array, cam, p_cls):
    # Resize CAM to exactly match the image dimensions (avoids broadcast errors)
    h, w = img_array.shape[:2]
    cam_resized = cv2.resize(cam, (w, h))
    heatmap = cv2.applyColorMap(np.uint8(255 * cam_resized), cv2.COLORMAP_JET)
    heatmap = np.float32(heatmap) / 255
    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
    
    img_float = np.float32(img_array) / 255
    gradcam_img = heatmap + img_float
    gradcam_img = gradcam_img / np.max(gradcam_img)
    return np.uint8(255 * gradcam_img)


# Biến toàn cục để giữ model trong bộ nhớ thay vì load lại mỗi lần gọi
yolo_model = None
cnn_model = None
device = None
img_transform = None
model_lock = threading.Lock()

YOLO_CONF = float(os.environ.get("YOLO_CONF", "0.10"))
# Accuracy-first by default.
# Set FAST_INFERENCE=1 to enable aggressive speed optimizations.
FAST_INFERENCE = os.environ.get("FAST_INFERENCE", "0") == "1"
YOLO_IMGSZ = int(os.environ.get("YOLO_IMGSZ", "640"))
YOLO_MAX_SIDE = int(os.environ.get("YOLO_MAX_SIDE", "1280"))
AI_PROFILE = os.environ.get("AI_PROFILE", "0") == "1"


def _timing_log(msg: str):
    if AI_PROFILE:
        sys.stderr.write(msg + "\n")


def _prepare_yolo_image(img_array):
    """Downscale oversized images for faster YOLO inference."""
    _ensure_imports()
    if not FAST_INFERENCE:
        return img_array, 1.0

    h, w = img_array.shape[:2]
    max_side = max(h, w)
    if max_side <= YOLO_MAX_SIDE:
        return img_array, 1.0

    scale = YOLO_MAX_SIDE / float(max_side)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    resized = cv2.resize(img_array, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, scale

def get_device():
    global device
    if device is not None:
        return device
    _ensure_imports()
    
    if hasattr(torch, 'cuda') and torch.cuda.is_available():
        device = torch.device('cuda')
    elif hasattr(torch, 'backends') and hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = torch.device('mps')
    else:
        device = torch.device('cpu')
        
    sys.stderr.write(f"Using device: {device}\n")
    return device

def load_models():
    global yolo_model, cnn_model, img_transform
    _ensure_imports()
    target_device = get_device()

    # Fast path: already ready
    if yolo_model is not None and cnn_model is not None and img_transform is not None:
        return

    with model_lock:
        # Double-check inside lock to avoid duplicate loading under concurrent requests
        if yolo_model is not None and cnn_model is not None and img_transform is not None:
            return
        try:
            # Load YOLO
            yolo_path = os.path.join(os.getcwd(), 'models', 'yolo_best.pt')
            yolo_model = YOLO(yolo_path)
            # Force YOLO to use CPU because MPS backend has NMS bugs resulting in 0 boxes
            yolo_model.to(torch.device('cpu'))

            # Load CNN
            cnn_model = models.efficientnet_b0(pretrained=False)
            cnn_model.classifier[1] = nn.Sequential(
                nn.Dropout(p=0.3),
                nn.Linear(cnn_model.classifier[1].in_features, 4)
            )
            eff_path = os.path.join(os.getcwd(), 'models', 'efficientnet_final.pth')
            cnn_model.load_state_dict(torch.load(eff_path, map_location=target_device))
            cnn_model.to(target_device)
            cnn_model.eval()
            img_transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
            ])

            sys.stderr.write("Models loaded successfully\n")
        except Exception as e:
            print(f"Error loading models: {e}")
            raise e

def predict_image(image_path: str, model_choice: str = 'ensemble'):
    """
    Dự đoán ảnh u não.
    model_choice: 'yolo', 'cnn', hoặc 'ensemble'
    Trả về (prediction_result, confidence, output_image_path)
    """
    load_models()
    t0 = time.perf_counter()
    
    try:
        image = Image.open(image_path).convert('RGB')
        img_array = np.array(image)
    except Exception as e:
        raise ValueError(f"Invalid image file: {e}")

    result_img = img_array.copy()
    h, w = img_array.shape[:2]
    _timing_log(f"[AI] load image: {(time.perf_counter()-t0):.3f}s")

    if model_choice == 'cnn':
        # Chỉ dùng thuật toán CNN trên toàn bộ ảnh
        t_cnn = time.perf_counter()
        with torch.inference_mode():
            input_tensor = img_transform(image).unsqueeze(0).to(get_device())
            out = cnn_model(input_tensor)
            prob, idx = torch.max(torch.nn.functional.softmax(out, dim=1), 1)
            p_cls = CLASSES[idx.item()]
            p_conf = prob.item() * 100
        _timing_log(f"[AI] cnn-only inference: {(time.perf_counter()-t_cnn):.3f}s")
        
        # Vẽ một label nhỏ góc trên
        cv2.putText(result_img, f"CNN: {p_cls} {p_conf:.1f}%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 30, 30), 2)
        
        # Tắt Grad-CAM để tối ưu tốc độ trên Mac
        gradcam_path = None
        zoom_path = None
        # try:
        #     grad_cam = GradCAM(cnn_model, cnn_model.features[-1])
        #     cam_mask = grad_cam(input_tensor, idx.item())
        #     cam_overlay = apply_gradcam_overlay(img_array, cam_mask[0], p_cls)
        #     gradcam_filename = "gradcam_" + os.path.basename(image_path)
        #     gradcam_path = os.path.join(UPLOAD_DIR, gradcam_filename)
        #     cv2.imwrite(gradcam_path, cam_overlay)
        # except Exception as e:
        #     print(f"GradCAM CNN Error: {e}")
            
        annotated_path = save_annotated_image(result_img, image_path)
        return p_cls, p_conf, annotated_path, gradcam_path, zoom_path

    # YOLO Dự đoán (Cho cả YOLO độc lập và Ensemble)
    t_yolo = time.perf_counter()
    yolo_input, scale = _prepare_yolo_image(img_array)
    if FAST_INFERENCE:
        res = yolo_model(yolo_input, conf=YOLO_CONF, imgsz=YOLO_IMGSZ, verbose=False)[0]
    else:
        # Preserve previous behavior for best accuracy.
        res = yolo_model(yolo_input, conf=YOLO_CONF, verbose=False)[0]

    # Retry once with a softer threshold to reduce false negatives.
    if len(res.boxes) == 0 and YOLO_CONF > 0.10:
        retry_conf = 0.10
        if FAST_INFERENCE:
            res = yolo_model(yolo_input, conf=retry_conf, imgsz=YOLO_IMGSZ, verbose=False)[0]
        else:
            res = yolo_model(yolo_input, conf=retry_conf, verbose=False)[0]
        _timing_log(f"[AI] yolo retry with lower conf={retry_conf}")
    _timing_log(f"[AI] yolo inference: {(time.perf_counter()-t_yolo):.3f}s")
    detected_tumors = []
    
    if len(res.boxes) == 0:
        return "No Tumor", 100.0, save_annotated_image(result_img, image_path), None, None

    ensemble_candidates = []

    for box in res.boxes:
        bx, by, bw, bh = box.xywh[0]
        bx, by, bw, bh = bx.item(), by.item(), bw.item(), bh.item()
        if scale != 1.0:
            bx /= scale
            by /= scale
            bw /= scale
            bh /= scale
        
        yolo_cls_idx = int(box.cls[0].item())
        yolo_p_cls = res.names[yolo_cls_idx]
        yolo_p_conf = box.conf[0].item()
        
        pad_w, pad_h = int(bw * 0.3), int(bh * 0.3)
        x1, y1 = max(0, int(bx - bw/2 - pad_w)), max(0, int(by - bh/2 - pad_h))
        x2, y2 = min(w, int(bx + bw/2 + pad_w)), min(h, int(by + bh/2 + pad_h))
        
        if model_choice == 'yolo':
            p_cls = yolo_p_cls
            p_conf = yolo_p_conf
            detected_tumors.append({
                "cls": p_cls, "conf": p_conf, 
                "box": (x1, y1, x2, y2), "crop_img": img_array[y1:y2, x1:x2],
                "idx": None, "tensor": None
            })
        else:
            # Ensemble: YOLO finds Box, CNN classifies the Crop
            if x2 > x1 and y2 > y1:
                crop_arr = img_array[y1:y2, x1:x2]
                detected_tumors.append({
                    "cls": "Unknown", "conf": 0.0,
                    "box": (x1, y1, x2, y2), "crop_img": crop_arr,
                    "idx": None, "tensor": None
                })
                ensemble_candidates.append(len(detected_tumors) - 1)
            else:
                p_cls = "Unknown"
                p_conf = 0.0
                detected_tumors.append({
                    "cls": p_cls, "conf": p_conf,
                    "box": (x1, y1, x2, y2), "crop_img": None,
                    "idx": None, "tensor": None
                })

    # Batch CNN for ensemble mode to reduce per-box overhead
    if model_choice != 'yolo' and ensemble_candidates:
        t_cnn_batch = time.perf_counter()
        batch_tensors = []
        valid_indices = []
        for idx in ensemble_candidates:
            crop_img = detected_tumors[idx]["crop_img"]
            if crop_img is None or crop_img.size == 0:
                continue
            crop_pil = Image.fromarray(crop_img)
            batch_tensors.append(img_transform(crop_pil))
            valid_indices.append(idx)

        if batch_tensors:
            with torch.inference_mode():
                input_batch = torch.stack(batch_tensors, dim=0).to(get_device())
                out = cnn_model(input_batch)
                probs = torch.nn.functional.softmax(out, dim=1)
                confs, idxs = torch.max(probs, dim=1)

            for i, tumor_idx in enumerate(valid_indices):
                cls_idx = idxs[i].item()
                conf = confs[i].item()
                detected_tumors[tumor_idx]["cls"] = CLASSES[cls_idx]
                detected_tumors[tumor_idx]["conf"] = conf
                detected_tumors[tumor_idx]["idx"] = cls_idx

        _timing_log(f"[AI] ensemble cnn batch: {(time.perf_counter()-t_cnn_batch):.3f}s")

    # Draw boxes/labels after predictions are ready
    for tumor in detected_tumors:
        x1, y1, x2, y2 = tumor["box"]
        p_cls = tumor["cls"]
        p_conf = tumor["conf"]
        cv2.rectangle(result_img, (x1, y1), (x2, y2), (255, 30, 30), 3)
        label = f"{p_cls} {p_conf*100:.1f}%"
        cv2.putText(result_img, label, (x1, max(20, y1-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 30, 30), 2)
    
    if detected_tumors:
        # Lấy u có độ tự tin cao nhất
        best_tumor = max(detected_tumors, key=lambda x: x["conf"])
        
        # Lưu ảnh cắt khối u (Zoom)
        gradcam_path = None
        zoom_path = None
        crop_img = best_tumor["crop_img"]
        if crop_img is not None and crop_img.size > 0:
            zoom_filename = "zoom_" + os.path.basename(image_path)
            zoom_abs_path = os.path.join(UPLOAD_DIR, zoom_filename)
            cv2.imwrite(zoom_abs_path, cv2.cvtColor(crop_img, cv2.COLOR_RGB2BGR))
            zoom_path = os.path.join(os.path.dirname(image_path), zoom_filename)
            
        # Tắt Grad-CAM để tối ưu tốc độ trên Mac
        if False: # best_tumor["tensor"] is not None and best_tumor["cls"] != "Unknown" and model_choice == 'ensemble':
            try:
                grad_cam = GradCAM(cnn_model, cnn_model.features[-1])
                cam_mask = grad_cam(best_tumor["tensor"], best_tumor["idx"])
                cam_overlay = apply_gradcam_overlay(best_tumor["crop_img"], cam_mask[0], p_cls)
                gradcam_filename = "gradcam_" + os.path.basename(image_path)
                gradcam_abs_path = os.path.join(UPLOAD_DIR, gradcam_filename)
                cv2.imwrite(gradcam_abs_path, cam_overlay)
                gradcam_path = os.path.join(os.path.dirname(image_path), gradcam_filename)
            except Exception as e:
                print(f"GradCAM Error: {e}")
                gradcam_path = None

        annotated_path = save_annotated_image(result_img, image_path)
        _timing_log(f"[AI] total predict_image: {(time.perf_counter()-t0):.3f}s")
        return best_tumor["cls"], best_tumor["conf"] * 100, annotated_path, gradcam_path, zoom_path
    else:
        annotated_path = save_annotated_image(result_img, image_path)
        _timing_log(f"[AI] total predict_image: {(time.perf_counter()-t0):.3f}s")
        return "No Tumor", 100.0, annotated_path, None, None

def save_annotated_image(img_array, original_path):
    """
    Lưu ảnh đã vẽ bounding box vào thư mục uploads
    """
    _ensure_imports()
    filename = os.path.basename(original_path)
    dir_name = os.path.dirname(original_path)
    annotated_filename = "annotated_" + filename
    annotated_path = os.path.join(dir_name, annotated_filename)
    
    # OpenCV uses BGR, need to convert from RGB back to BGR for saving
    bgr_img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    cv2.imwrite(annotated_path, bgr_img)
    return annotated_path
