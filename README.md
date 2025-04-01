# KneeSync API

## Overview

HealStep API is a FastAPI-based backend for collecting and managing knee angle and EMG readings from an **MPU6050** and **MyoWare Muscle Sensor 2.0**. It stores the data in a **PostgreSQL** database and provides endpoints for data retrieval and management.

# Update Api cmd
cd Healstep-API 
git pull 
sudo docker stop kneesync
sudo docker buildx build -t kneesync .
sudo docker run -p 8000:8000 kneesync




