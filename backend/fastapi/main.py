from fastapi import FastAPI, HTTPException
import requests
import pandas as pd
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware



# 환경 변수 로드
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인을 허용하거나 특정 도메인을 명시할 수 있습니다.
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메소드를 허용합니다.
    allow_headers=["*"],  # 모든 헤더를 허용합니다.
)

# 환경 변수 설정 (API Key & URL)
API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")

# 🚀 1. CSV 파일 로드하여 노드 & 링크 데이터 매핑 생성
coord_file_path = "../../data/coord/coord_utf.csv"
link_file_path = "../../data/coord/link_utf.csv"


try:
    # 노드 좌표 로드
    df_coord = pd.read_csv(coord_file_path, encoding="utf-8")
    NODE_COORDINATES = {str(row["NODE_ID"]): [row["x"], row["y"]] for _, row in df_coord.iterrows()}
    print("✅ 노드 데이터 로드 완료!")

    # 도로 링크 정보 로드
    df_link = pd.read_csv(link_file_path, encoding="utf-8")
    LINK_INFO = {
        str(row["LINK_ID"]): {
            "start_node": str(row["F_NODE"]),
            "end_node": str(row["T_NODE"]),
            "road_name": row["ROAD_NAME"],
            "max_speed": row["MAX_SPD"],
            "length": row["LENGTH"]
        }
        for _, row in df_link.iterrows()
    }
    print("✅ 도로 링크 데이터 로드 완료!")

except Exception as e:
    print(f"❌ 데이터 로드 실패: {e}")
    NODE_COORDINATES = {}
    LINK_INFO = {}

@app.get("/traffic")
def get_traffic_data():
    """
    서울시 ITS API에서 교통 데이터를 가져와 GeoJSON 변환
    """
    params = {
        "apiKey": API_KEY,
        "type": "all",
        "minX": "126.73",
        "maxX": "127.26",
        "minY": "37.41",
        "maxY": "37.71",
        "getType": "json"
    }
    
    response = requests.get(API_URL, params=params)
    data = response.json()

    if data["header"]["resultCode"] != 0:
        return {"error": "Failed to fetch traffic data"}

    # 🚀 2. GeoJSON 변환 (링크 ID를 기반으로 노드 간 선(LineString) 생성)
    features = []
    for item in data["body"]["items"]:
        link_id = str(item["linkId"])

        if link_id in LINK_INFO:
            start_id = LINK_INFO[link_id]["start_node"]
            end_id = LINK_INFO[link_id]["end_node"]

            # 노드 ID를 위경도로 변환
            if start_id in NODE_COORDINATES and end_id in NODE_COORDINATES:
                start_coords = NODE_COORDINATES[start_id]  # [경도, 위도]
                end_coords = NODE_COORDINATES[end_id]  # [경도, 위도]

                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [start_coords, end_coords]
                    },
                    "properties": {
                        "roadName": LINK_INFO[link_id]["road_name"],
                        "speed": float(item["speed"]),
                        "maxSpeed": LINK_INFO[link_id]["max_speed"],
                        "travelTime": float(item["travelTime"]),
                        "length": LINK_INFO[link_id]["length"]
                    }
                })
        else:
            print(f"🚨 링크 {link_id}의 도로 정보 없음 (무시됨)")

    return {"type": "FeatureCollection", "features": features}
