<p align="center">
  <img src="./Banner.png" alt="Predictive Maintenance in Oil & Gas" width="100%">
</p>


# 🔧 **AI-Driven Predictive Maintenance for Oil & Gas | Remaining Useful Life (RUL) Estimation**

A full end-to-end **machine learning system** for predicting Remaining Useful Life (RUL) in rotating equipment used in the **oil & gas industry**.  
This project features:

✔️ Feature-engineered turbomachinery sensor dataset  
✔️ XGBoost & Neural Network regression models  
✔️ Ensemble RUL prediction  
✔️ Production-ready **FastAPI inference server**  
✔️ **Streamlit UI** for business-friendly visualization  
✔️ Clean modular project structure suitable for real deployment

---

# 📘 **1. Executive Summary**

Rotating equipment failures (pumps, compressors, turbines) are a major source of unplanned downtime in the energy sector.  
Traditional maintenance strategies—reactive or fixed-interval—often lead to:

- Costly shutdowns  
- Equipment over-maintenance  
- Safety and environmental risks

This project provides an **AI-powered predictive maintenance solution** that estimates RUL from vibration, thermal, acoustic, and derived sensor indicators.

📌 **Business Value**  
- Reduce unplanned downtime  
- Improve maintenance planning  
- Optimize asset integrity & operational efficiency  
- Enable data-driven reliability engineering

---

# 📂 **2. Project Architecture**

```
asset-integrity-predictive-maintenance/
│
├── data/                          → Raw NASA C-MAPSS dataset (not committed)
│   ├── train_FD001.txt
│   ├── test_FD001.txt
│   └── RUL_FD001.txt
│
├── notebooks/
│   ├── EDA_clean.ipynb            → Exploratory data analysis
│   └── Modeling_clean_fixed.ipynb → Feature engineering & model training
│
├── models/                        → API-ready models & inference artifacts
│   ├── xgb_model.pkl
│   ├── neural_network_rul.keras
│   ├── linear_regression.pkl
│   ├── minmax_scaler.pkl
│   └── feature_names.json
│
├── scripts/
│   ├── train_xgboost.py           → XGBoost training pipeline
│   ├── train_lstm.py              → LSTM model training
│   └── utils.py                   → Shared preprocessing utilities
│
├── Streamlit_app/
│   └── app.py                     → Streamlit frontend UI
│
├── rul_api.py                     → FastAPI inference backend
├── README.md                      → Project documentation
├── requirements.txt               → Python dependencies
├── .gitignore
└── Banner.png                     → Repository header graphic

```

---

# 🧠 **3. Machine Learning Workflow**

### **3.1 Data Processing**
- Missing-value handling  
- Scaling & normalization  
- Rolling statistics (mean, std)  
- Trend-based degradation features  

### **3.2 Modeling**
| Model | Description |
|-------|-------------|
| **XGBoost Regressor** | High-performance baseline model |
| **Deep Neural Network (.keras)** | Learns complex non-linear degradation patterns |
| **Ensemble (Average)** | Improves robustness & reduces variance |

### **3.3 Evaluation Metrics**
- MAE (Mean Absolute Error)  
- RMSE (Root Mean Squared Error)  

> The ensemble model delivered the most stable predictions across failure cycles.

---

# 🚀 **4. Production-Ready Inference API (FastAPI)**

The backend provides programmatic RUL predictions for any input sensor vector.

### Run the API  
```bash
uvicorn rul_api:app --reload
```

### API Documentation  
Open your browser:  
👉 **http://127.0.0.1:8000/docs**

You’ll see:
- Interactive Swagger UI  
- POST `/predict_rul` that returns:  
```json
{
  "xgb_rul": 133.83,
  "nn_rul": 127.55,
  "ensemble_rul": 130.69
}
```

---

# 🖥️ **5. User Interface (Streamlit)**

A clean, interactive dashboard for non-technical users (engineers, reliability managers).

### Launch Streamlit UI  
```bash
streamlit run Streamlit_app/app.py
```

### Features:
- Sidebar with 153 sensor inputs  
- API request status & prediction visualization  
- XGBoost, Neural Net, and Ensemble comparison  
- Expandable raw JSON outputs  

Perfect for **presentations, interviews, and industrial demos**.

---

# 📊 **6. Dataset**

- **Source:** NASA C-MAPSS Turbofan Degradation dataset  
- **Adapted for oil & gas:**  
  Turbofan sensors mapped to rotating equipment (pumps, compressors)

| Category | Examples |
|----------|----------|
| Operational settings | Temperature, pressure, fuel flow |
| Sensor channels | Vibration, acoustic, torque, thermal readings |
| Engine cycles | Operating hours (proxy for degradation) |

---

# 📈 **7. Results Summary**

### Key Insights:
- Rolling statistics improved signal clarity  
- XGBoost captured failure curves effectively  
- Neural network captured non-linear wear patterns  
- Ensemble delivered the most **stable** predictions across test samples

📌 *This mirrors real-world predictive maintenance systems where ensemble models outperform single estimators.*

---

# 🛠️ **8. Tech Stack**

### **Languages & ML Tools**
- Python, NumPy, pandas  
- scikit-learn  
- XGBoost  
- TensorFlow / Keras  

### **APIs & Deployment**
- FastAPI  
- Uvicorn  
- Streamlit  

### **Environment & MLOps**
- Conda / virtual environments  
- Git & GitHub  
- Jupyter Notebooks  

---

# 🌍 **9. How to Reproduce**

### 1️⃣ Clone Repo  
```bash
git clone https://github.com/<your-username>/asset-integrity-predictive-maintenance.git
cd asset-integrity-predictive-maintenance
```

### 2️⃣ Create Environment  
```bash
conda create -n tfenv python=3.11
conda activate tfenv
pip install -r requirements.txt
```

### 3️⃣ Run Backend  
```
uvicorn rul_api:app --reload
```

### 4️⃣ Run Frontend  
```
streamlit run scripts/streamlit_app.py
```

---

# 🏭 **10. Industrial Applications**

This system can be deployed across:

- Oil & gas rotating machinery  
- Petrochemical pumps & compressors  
- Refinery turbomachinery  
- Offshore platform maintenance  
- LNG plant reliability systems  

---

# 👤 **Author**

**Mohamed Jamaludeen Hussain**  
Data Analytics Graduate Student | Asset Integrity Specialist | Oil & Gas Professional  

📌 *Bridging 15+ years of industrial experience with machine learning innovation.*  
📧 mojh2088@gmail.com  
🔗 **LinkedIn:**  
https://www.linkedin.com/in/mohamed-jamaludeen-hussain-shaik-munavar-hussain-9289a8a1/


---

# ⭐ **If you found this project valuable, please star the repository!**
