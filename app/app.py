import streamlit as st
import cv2
import torch
import numpy as np
from PIL import Image
from torchvision import transforms, models
from ultralytics import YOLO
import torch.nn as nn

# 1. WEB PAGE CONFIGURATION
st.set_page_config(page_title="AI Brain Tumor Diagnosis", page_icon="🧠", layout="centered")
st.title("🧠 AI Brain Tumor Diagnosis App (MRI)")
st.markdown("**Model:** Hybrid V6 (YOLOv11s + EfficientNet-B0) | **Accuracy:** ~95%")
st.markdown("---")

CLASSES = ['Glioma', 'Meningioma', 'No Tumor', 'Pituitary']

# 2. MODEL LOADING FUNCTION (Cache to avoid lag)
@st.cache_resource
def load_models():
    # Load YOLO from local files
    yolo = YOLO('yolo_best.pt') 
    
    # Load CNN from local files
    cnn = models.efficientnet_b0(pretrained=False)
    cnn.classifier[1] = nn.Sequential(
        nn.Dropout(p=0.3), 
        nn.Linear(cnn.classifier[1].in_features, 4)
    )
    # Force CPU mode to avoid failures on devices without dedicated GPU
    cnn.load_state_dict(torch.load('efficientnet_final.pth', map_location=torch.device('cpu')))
    cnn.eval()
    
    return yolo, cnn

# Initialize models
with st.spinner("Initializing AI models... (first run takes a few seconds)"):
    try:
        yolo_model, cnn_model = load_models()
    except Exception as e:
        st.error(f"❌ Failed to load model files. Make sure 'yolo_best.pt' and 'efficientnet_final.pth' are in the same directory as app.py. Error: {e}")
        st.stop()

# 3. MAIN UI
uploaded_file = st.file_uploader("Upload a brain MRI image (JPG, PNG)", type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None:
    # Read image
    image = Image.open(uploaded_file).convert('RGB')
    img_array = np.array(image)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📸 Original Image")
        st.image(image, use_column_width=True)

    with col2:
        st.subheader("🔬 Analysis Result")
        with st.spinner('AI is analyzing the image...'):
            # YOLO prediction
            res = yolo_model(img_array, conf=0.25, verbose=False)[0]
            result_img = img_array.copy()
            
            if len(res.boxes) == 0:
                st.success("🎉 Conclusion: NO BRAIN TUMOR DETECTED (No Tumor)")
                st.image(result_img, use_column_width=True)
            else:
                # Tumor detected -> crop region and classify with CNN
                transform = transforms.Compose([
                    transforms.Resize((224, 224)), transforms.ToTensor(),
                    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
                ])
                h, w = img_array.shape[:2]
                detected_tumors = []
                
                for box in res.boxes:
                    bx, by, bw, bh = box.xywh[0]
                    bx, by, bw, bh = bx.item(), by.item(), bw.item(), bh.item()
                    
                    pad_w, pad_h = int(bw * 0.3), int(bh * 0.3)
                    x1, y1 = max(0, int(bx - bw/2 - pad_w)), max(0, int(by - bh/2 - pad_h))
                    x2, y2 = min(w, int(bx + bw/2 + pad_w)), min(h, int(by + bh/2 + pad_h))
                    
                    if x2 > x1 and y2 > y1:
                        crop = Image.fromarray(img_array[y1:y2, x1:x2])
                        with torch.no_grad():
                            out = cnn_model(transform(crop).unsqueeze(0))
                            prob, idx = torch.max(torch.nn.functional.softmax(out, dim=1), 1)
                            
                        p_cls = CLASSES[idx.item()]
                        p_conf = prob.item()
                        detected_tumors.append((p_cls, p_conf))
                        
                        # Draw bounding box and label
                        cv2.rectangle(result_img, (x1, y1), (x2, y2), (255, 30, 30), 3)
                        label = f"{p_cls} {p_conf*100:.1f}%"
                        cv2.putText(result_img, label, (x1, max(20, y1-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 30, 30), 2)
                
                st.image(result_img, use_column_width=True)
                if detected_tumors:
                    for p_cls, p_conf in detected_tumors:
                        st.warning(f"⚠️ Warning: AI detected suspicious structures, possible **{p_cls}** (Confidence: {p_conf*100:.1f}%).")
                else:
                    st.success("🎉 Conclusion: NO BRAIN TUMOR DETECTED (or no valid tumor region recognized)")
