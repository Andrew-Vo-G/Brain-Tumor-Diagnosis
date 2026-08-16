# Brain Tumor Diagnosis

<p align="center">
  <img src="app/frontend/assets/brain-placeholder.svg" alt="Brain tumor diagnosis overview" width="180" />
</p>

AI-assisted MRI analysis system for brain tumor detection and classification. The project combines YOLO-based tumor localization with a CNN classifier and provides a lightweight web interface for image upload, result review, and clinical-style visualization.

## Overview

This project is designed to process MRI scans and identify potential tumor regions with a hybrid pipeline:

- object detection to localize suspicious areas
- classification to predict tumor type
- web interface for image upload and quick review
- backend APIs for patient/doctor workflow support

Supported classes:

- Glioma
- Meningioma
- No Tumor
- Pituitary

## Architecture

```text
MRI Image
  -> YOLO detection
  -> ROI extraction
  -> EfficientNet classification
  -> Result + confidence + visualization
```

## Tech Stack

- Python
- PyTorch
- Ultralytics YOLO
- OpenCV
- FastAPI
- Streamlit
- NumPy / Pillow
- JWT authentication

## Repository Structure

```text
BrainTumor_Project/
├── app/
│   ├── app.py
│   ├── backend/
│   └── frontend/
├── data/
├── docs/
├── models/
├── Dockerfile
├── LICENSE
├── README.md
├── requirements.txt
├── Start_BrainAI.command
└── venv/
```

## Run locally

1. Create and activate a virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Place model weights in the models folder

```text
models/
├── yolo_best.pt
├── efficientnet_final.pth
```

4. Start the API

```bash
cd app
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

5. Start the UI

```bash
streamlit run app.py
```

## Sample outputs

### Notebook / model visualization

<p align="center">
  <table>
    <tr>
      <td align="center">
        <img src="docs/brain_tumor_yolo_1.png" alt="YOLO training visualization 1" width="260" />
      </td>
      <td align="center">
        <img src="docs/brain_tumor_yolo_2.png" alt="YOLO training visualization 2" width="260" />
      </td>
      <td align="center">
        <img src="docs/brain_tumor_yolo_3.png" alt="YOLO training visualization 3" width="260" />
      </td>
    </tr>
    <tr>
      <td align="center">
        <img src="docs/brain_tumor_yolo_4.png" alt="YOLO training visualization 4" width="260" />
      </td>
      <td align="center">
        <img src="data/mri_test.jpg" alt="MRI sample" width="260" />
      </td>
      <td align="center">
        <img src="data/test_inference.jpg" alt="Inference example" width="260" />
      </td>
    </tr>
  </table>
</p>

### MRI examples

<p align="center">
  <table>
    <tr>
      <td align="center">
        <img src="data/annotated_mri_test.jpg" alt="Annotated MRI sample" width="260" />
        <br>Annotated MRI
      </td>
      <td align="center">
        <img src="data/zoom_mri_test.jpg" alt="Zoomed MRI crop" width="260" />
        <br>Zoomed region
      </td>
      <td align="center">
        <img src="data/annotated_Tr-me_0100.jpg" alt="Tumor MRI sample" width="260" />
        <br>Detected lesion area
      </td>
    </tr>
  </table>
</p>

## Notes

- This is a research and prototype project, not a medical device.
- Large model files are excluded from GitHub by default because of file-size limitations.
- For production use, model validation, data privacy review, and clinical testing are required.

## License

This project is licensed under the MIT license. See [LICENSE](LICENSE).
