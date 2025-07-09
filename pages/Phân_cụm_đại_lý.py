import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import plotly.express as px
from utils.data_loader import load_inventory_data

# Tiêu đề ứng dụng
st.set_page_config(page_title="Phân Tích Đại Lý", layout="wide")
st.title("🏪 Phân Tích & Phân Nhóm Đại Lý")
st.markdown("""
**Phân cụm đại lý dựa trên 5 đặc trưng quan trọng:**  
1. Độ đa dạng SKU  
2. Cường độ nhập hàng  
3. Hệ số biến động  
4. Chỉ số tập trung  
5. Độ trễ thanh toán  
""")

## 1. Load và chuẩn bị dữ liệu
@st.cache_data
def load_data():
    try:
        _, ddh, px, ro, _ = load_inventory_data("data/du_lieu_phu_tung_thuc_te.xlsx")
        
        # Kết hợp dữ liệu từ phiếu xuất và đơn đặt hàng
        px = px.rename(columns={
            'Mã đại lý': 'ma_dl',
            'Mã phụ tùng': 'ma_pt',
            'Số lượng xuất': 'sl_xuat',
            'Ngày xuất hàng': 'ngay_xuat'
        })
        
        ddh = ddh.rename(columns={
            'Mã đại lý': 'ma_dl',
            'Mã phụ tùng': 'ma_pt',
            'Số lượng': 'sl_dat',
            'Ngày đặt hàng': 'ngay_dat'
        })
        
        return pd.concat([px[['ma_dl', 'ma_pt', 'sl_xuat', 'ngay_xuat']], 
                         ddh[['ma_dl', 'ma_pt', 'sl_dat', 'ngay_dat']]])
    
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu: {str(e)}")
        return pd.DataFrame()

dl_data = load_data()

if dl_data.empty:
    st.stop()

## 2. Tính toán các đặc trưng
def calculate_agency_features(data):
    # Chuyển đổi ngày
    data['ngay_xuat'] = pd.to_datetime(data['ngay_xuat'])
    data['ngay_dat'] = pd.to_datetime(data['ngay_dat'])
    
    # Tính toán cho từng đại lý
    features = data.groupby('ma_dl').agg({
        'ma_pt': ['nunique', 'count'],  # Đếm số SKU khác nhau và tổng lần nhập
        'sl_xuat': ['sum', 'mean', 'std'],  # Tổng, TB và độ lệch số lượng xuất
        'ngay_xuat': ['min', 'max']  # Ngày đầu và cuối
    }).reset_index()
    
    # Làm phẳng multi-index columns
    features.columns = ['ma_dl', 'sku_da_dang', 'tong_lan_nhap', 
                      'tong_xuat', 'tb_xuat', 'do_lech_xuat',
                      'ngay_dau', 'ngay_cuoi']
    
    # Tính các đặc trưng
    features['thoi_gian_hoat_dong'] = (features['ngay_cuoi'] - features['ngay_dau']).dt.days
    features['cuong_do_nhap'] = features['tong_xuat'] / (features['thoi_gian_hoat_dong']/30)  # SP/tháng
    features['he_so_bien_dong'] = features['do_lech_xuat'] / features['tb_xuat']
    features['chi_so_tap_trung'] = 1  # Tạm thời, sẽ tính sau
    
    # Xử lý giá trị vô cùng và NaN
    features.replace([np.inf, -np.inf], np.nan, inplace=True)
    features.fillna(0, inplace=True)
    
    return features

with st.spinner('Đang tính toán đặc trưng đại lý...'):
    agency_features = calculate_agency_features(dl_data)

## 3. Phân cụm đại lý
def cluster_agencies(features_df):
    # Chuẩn hóa dữ liệu
    scaler = StandardScaler()
    X = features_df[['sku_da_dang', 'cuong_do_nhap', 'he_so_bien_dong', 'chi_so_tap_trung']]
    X_scaled = scaler.fit_transform(X)
    
    # Phân cụm K-means
    kmeans = KMeans(n_clusters=6, random_state=42)
    features_df['cluster'] = kmeans.fit_predict(X_scaled)
    
    # Gán nhãn cho các cụm
    features_df['nhom'] = features_df['cluster'].map({
        0: 'Nhóm 1: Đại lý toàn diện',
        1: 'Nhóm 2: Đại lý chuyên biệt ổn định',
        2: 'Nhóm 3: Đại lý mùa vụ',
        3: 'Nhóm 4: Đại lý nhỏ rủi ro cao',
        4: 'Nhóm 5: Đại lý chiến lược',
        5: 'Nhóm 6: Đại lý mới/đặc biệt'
    })
    
    return features_df

with st.spinner('Đang phân nhóm đại lý...'):
    clustered_agencies = cluster_agencies(agency_features)

## 4. Hiển thị kết quả
st.write("## Kết quả phân nhóm đại lý")

# Tạo tabs
tab1, tab2, tab3 = st.tabs(["Phân bổ nhóm", "Đặc trưng từng nhóm", "Chiến lược quản lý"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        # Biểu đồ Pie
        fig_pie = px.pie(
            clustered_agencies,
            names='nhom',
            title='Phân bổ các nhóm đại lý',
            hole=0.3,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Biểu đồ Bar
        count_data = clustered_agencies['nhom'].value_counts().reset_index()
        fig_bar = px.bar(
            count_data,
            x='nhom',
            y='count',
            title='Số lượng đại lý từng nhóm',
            text='count',
            color='nhom',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_bar.update_traces(textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True)

with tab2:
    # Thống kê đặc trưng các nhóm
    st.write("### Đặc trưng trung bình từng nhóm")
    
    group_stats = clustered_agencies.groupby('nhom').agg({
        'sku_da_dang': 'mean',
        'cuong_do_nhap': 'mean',
        'he_so_bien_dong': 'mean',
        'chi_so_tap_trung': 'mean'
    }).reset_index()
    
    # Hiển thị bảng
    st.dataframe(
        group_stats.style.format({
            'sku_da_dang': '{:.1f}',
            'cuong_do_nhap': '{:.1f}',
            'he_so_bien_dong': '{:.2f}',
            'chi_so_tap_trung': '{:.2f}'
        }).background_gradient(cmap='Blues'),
        use_container_width=True
    )
    
    # Biểu đồ radar
    fig_radar = px.line_polar(
        group_stats, 
        r='cuong_do_nhap', 
        theta='nhom',
        line_close=True,
        title='Cường độ nhập hàng theo nhóm'
    )
    st.plotly_chart(fig_radar, use_container_width=True)

with tab3:
    # Chiến lược quản lý từng nhóm
    st.write("### Chiến lược quản lý theo nhóm")
    
    selected_group = st.selectbox(
        "Chọn nhóm đại lý",
        options=clustered_agencies['nhom'].unique()
    )
    
    strategies = {
        'Nhóm 1: Đại lý toàn diện': [
            "Áp dụng mô hình dự báo chi tiết từng SKU",
            "Tự động hóa quy trình đặt hàng",
            "Quản trị tồn kho chủ động",
            "Ưu tiên nguồn lực hỗ trợ"
        ],
        'Nhóm 2: Đại lý chuyên biệt ổn định': [
            "Dự báo theo chu kỳ/định kỳ",
            "Gói dịch vụ chuyên biệt",
            "Kiểm soát tồn kho đơn giản",
            "Khuyến mãi theo nhóm sản phẩm chuyên biệt"
        ],
        'Nhóm 3: Đại lý mùa vụ': [
            "Dự báo có yếu tố thời vụ",
            "Cảnh báo đầu mùa vụ",
            "Chính sách đặt hàng trước mùa",
            "Linh hoạt nguồn hàng theo mùa"
        ],
        'Nhóm 4: Đại lý nhỏ rủi ro cao': [
            "Dự báo đơn giản theo cụm",
            "Kiểm soát tồn kho chặt chẽ",
            "Giới hạn ưu đãi",
            "Thanh toán trước hoặc COD"
        ],
        'Nhóm 5: Đại lý chiến lược': [
            "Ưu tiên giao hàng nhanh",
            "Dashboard theo dõi chuyên sâu",
            "Chính sách giá ưu đãi",
            "Hỗ trợ 24/7"
        ],
        'Nhóm 6: Đại lý mới/đặc biệt': [
            "Theo dõi riêng biệt",
            "Phân tích hành vi cá nhân hóa",
            "Chưa áp dụng dự báo tự động",
            "Chính sách thử nghiệm"
        ]
    }
    
    st.write(f"**Chiến lược cho {selected_group}:**")
    for strategy in strategies[selected_group]:
        st.write(f"- {strategy}")
    
    # Hiển thị danh sách đại lý thuộc nhóm
    st.write(f"**Danh sách đại lý {selected_group}:**")
    group_data = clustered_agencies[clustered_agencies['nhom'] == selected_group]
    st.dataframe(
        group_data[['ma_dl', 'sku_da_dang', 'cuong_do_nhap']]
            .sort_values('cuong_do_nhap', ascending=False),
        hide_index=True
    )

# Xuất dữ liệu
if st.button("Xuất kết quả phân tích"):
    with pd.ExcelWriter('phan_nhom_dai_ly.xlsx') as writer:
        clustered_agencies.to_excel(writer, index=False)
    st.success("Đã xuất file thành công!")