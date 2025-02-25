import pandas as pd
import folium

# 1️⃣ 노드 및 링크 데이터 로드 (파일 경로 직접 지정)
node_file_path = "data/coord/coord_utf.csv"
link_file_path = "data/coord/link_utf.csv"

node_df = pd.read_csv(node_file_path, encoding="utf-8", low_memory=False)
link_df = pd.read_csv(link_file_path, encoding="utf-8", low_memory=False)


# 2️⃣ 서울 지역 노드만 필터링
seoul_nodes = node_df[
    (node_df["x"] >= 126.7) & (node_df["x"] <= 127.3) &
    (node_df["y"] >= 37.3) & (node_df["y"] <= 37.7)
]

# 4️⃣ 서울 노드 리스트 생성
seoul_node_ids = set(seoul_nodes["NODE_ID"])

# 5️⃣ 서울 지역에 속하는 링크만 필터링 (출발 & 도착 노드가 둘 다 서울에 있는 경우)
seoul_links = link_df[
    (link_df["F_NODE"].isin(seoul_node_ids)) & 
    (link_df["T_NODE"].isin(seoul_node_ids))
]

# 6️⃣ 노드 데이터를 딕셔너리로 변환 (빠른 조회를 위해)
node_dict = seoul_nodes.set_index("NODE_ID")[["y", "x"]].to_dict(orient="index")

# 7️⃣ 서울 중심 좌표 설정
seoul_center = [37.5665, 126.9780]

# 8️⃣ Folium 지도 생성
m = folium.Map(location=seoul_center, zoom_start=12)

# 9️⃣ 서울 노드 데이터 지도에 추가 (파란색 점)
for node_id, coords in node_dict.items():
    folium.CircleMarker(
        location=[coords["y"], coords["x"]],
        radius=2,
        color="blue",
        fill=True,
        fill_color="blue",
        fill_opacity=0.6,
        tooltip=f"NODE_ID: {node_id}"
    ).add_to(m)

# 🔟 서울 도로 링크 지도에 추가 (빨간색 선)
for _, row in seoul_links.iterrows():
    f_node = row["F_NODE"]
    t_node = row["T_NODE"]

    # 시작 노드와 종료 노드 좌표 찾기
    if f_node in node_dict and t_node in node_dict:
        f_coords = node_dict[f_node]
        t_coords = node_dict[t_node]

        folium.PolyLine(
            locations=[(f_coords["y"], f_coords["x"]), (t_coords["y"], t_coords["x"])],
            color="red",
            weight=2,
            opacity=0.8,
            tooltip=f"도로명: {row['ROAD_NAME']}<br>제한 속도: {row['MAX_SPD']} km/h<br>길이: {row['LENGTH']} m"
        ).add_to(m)

# 🔟 지도 파일 저장
map_file = "seoul_link_map.html"
m.save(map_file)

print(f"서울 지역 지도 파일이 저장되었습니다: {map_file}")