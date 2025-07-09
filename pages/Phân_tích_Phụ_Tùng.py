import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from utils.data_loader import load_inventory_data

# Tiêu đề ứng dụng
st.set_page_config(page_title="Phân Tích Nhu Cầu Phụ Tùng", layout="wide")
st.title("Phân Tích & Phân Nhóm Phụ Tùng Theo Nhu Cầu")
st.markdown("""
**Tính toán các đặc trưng từ dữ liệu gốc và phân nhóm phụ tùng theo nhu cầu thực tế**
""")

## 1. Load và chuẩn bị dữ liệu
@st.cache_data
def load_and_prepare_data():
    try:
        # Load dữ liệu từ các sheet
        dmvt, ddh, phieu_xuat, ro, pn = load_inventory_data("data/du_lieu_phu_tung_thuc_te.xlsx")
        
        # Chuẩn hóa tên cột
        phieu_xuat = phieu_xuat.rename(columns={
            'Ngày xuất hàng': 'ngay_xuat',
            'Mã phụ tùng': 'ma_pt',
            'Số lượng xuất': 'sl_xuat'
        })
        
        dmvt = dmvt.rename(columns={
            'Mã phụ tùng': 'ma_pt', 
            'Tên phụ tùng': 'ten_pt'
        })
        
        return dmvt, phieu_xuat
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu: {str(e)}")
        return None, None

dmvt, phieu_xuat = load_and_prepare_data()

if dmvt is None or phieu_xuat is None:
    st.stop()

## 2. Tính toán các đặc trưng quan trọng
def calculate_features(phieu_xuat):
    # Chuyển đổi ngày
    phieu_xuat['ngay_xuat'] = pd.to_datetime(phieu_xuat['ngay_xuat'])
    phieu_xuat['thang'] = phieu_xuat['ngay_xuat'].dt.to_period('M')
    
    # Tính các đặc trưng cơ bản
    features = phieu_xuat.groupby('ma_pt').agg({
        'sl_xuat': ['sum', 'mean', 'std'],
        'ngay_xuat': ['count', lambda x: (x.max() - x.min()).days]
    }).reset_index()
    
    # Đặt tên cột
    features.columns = ['ma_pt', 'tong_xuat', 'trung_binh_xuat', 
                      'do_lech_chuan', 'so_lan_xuat', 'so_ngay_hoat_dong']
    
    # Xử lý các trường hợp đặc biệt
    features['so_ngay_hoat_dong'] = features['so_ngay_hoat_dong'].replace(0, 1)
    
    # Tính các đặc trưng phức tạp
    features['tan_suat'] = features['so_lan_xuat'] / (features['so_ngay_hoat_dong']/30)  # Số lần xuất/tháng
    features['khoang_cach_tb'] = features['so_ngay_hoat_dong'] / features['so_lan_xuat']  # Khoảng cách TB giữa các lần xuất (ngày)
    
    # Tính độ biến động (coefficient of variation)
    features['do_bien_dong'] = features['do_lech_chuan'] / features['trung_binh_xuat']
    
    # Tính tỷ lệ tháng có phát sinh
    monthly_sales = phieu_xuat.groupby(['ma_pt', 'thang'])['sl_xuat'].sum().reset_index()
    total_months = phieu_xuat['thang'].nunique()
    monthly_count = monthly_sales.groupby('ma_pt')['thang'].count().reset_index()
    monthly_count.columns = ['ma_pt', 'so_thang_co_xuat']
    features = pd.merge(features, monthly_count, on='ma_pt')
    features['ti_le_thang_xuat'] = features['so_thang_co_xuat'] / total_months
    
    # Xử lý giá trị vô cùng và NaN
    features.replace([np.inf, -np.inf], np.nan, inplace=True)
    features.fillna(0, inplace=True)
    
    return features

with st.spinner('Đang tính toán các đặc trưng từ dữ liệu...'):
    features = calculate_features(phieu_xuat)

# Hiển thị các đặc trưng đã tính
st.write("### Các đặc trưng đã tính toán")
st.dataframe(
    features.style.format({
        'tong_xuat': '{:,.0f}',
        'trung_binh_xuat': '{:.1f}',
        'do_lech_chuan': '{:.1f}',
        'tan_suat': '{:.2f}',
        'khoang_cach_tb': '{:.1f}',
        'do_bien_dong': '{:.2f}',
        'ti_le_thang_xuat': '{:.2%}'
    }),
    use_container_width=True
)

## 3. Phân cụm phụ tùng
def cluster_parts(features_df):
    # Chuẩn hóa dữ liệu
    scaler = StandardScaler()
    X = features_df[['trung_binh_xuat', 'do_bien_dong', 'tan_suat', 'ti_le_thang_xuat']]
    X_scaled = scaler.fit_transform(X)
    
    # Phân cụm K-means
    kmeans = KMeans(n_clusters=4, random_state=42)
    features_df['cluster'] = kmeans.fit_predict(X_scaled)
    
    # Gán nhãn cho các cụm
    features_df['nhom'] = features_df['cluster'].map({
        0: 'Nhóm A - Nhu cầu cao',
        1: 'Nhóm B - Mùa vụ',
        2: 'Nhóm C - Cố định',
        3: 'Nhóm D - Nhu cầu thấp'
    })
    
    return features_df

with st.spinner('Đang phân nhóm phụ tùng...'):
    clustered_data = cluster_parts(features)

# Kết hợp với thông tin danh mục
final_data = pd.merge(clustered_data, dmvt, on='ma_pt', how='left')

# 4. Hiển thị kết quả
st.write("## Kết quả phân nhóm phụ tùng")

# Tạo layout 2 cột
col1, col2 = st.columns(2)

with col1:
    # Biểu đồ Pie chart
    st.write("### Phân bổ tỷ lệ các nhóm")
    fig_pie = px.pie(
        final_data, 
        names='nhom', 
        title='Tỷ lệ các nhóm phụ tùng',
        hole=0.3,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    # Biểu đồ Bar chart
    st.write("### Số lượng phụ tùng từng nhóm")
    
    # Đếm số lượng phụ tùng mỗi nhóm
    count_data = final_data['nhom'].value_counts().reset_index()
    count_data.columns = ['nhom', 'so_luong']
    
    # Sắp xếp theo thứ tự nhóm A, B, C, D
    nhom_order = ['Nhóm A - Nhu cầu cao', 'Nhóm B - Mùa vụ', 
                 'Nhóm C - Cố định', 'Nhóm D - Nhu cầu thấp']
    count_data['nhom'] = pd.Categorical(count_data['nhom'], categories=nhom_order, ordered=True)
    count_data = count_data.sort_values('nhom')
    
    fig_bar = px.bar(
        count_data,
        x='nhom',
        y='so_luong',
        color='nhom',
        title='Số lượng phụ tùng mỗi nhóm',
        labels={'so_luong': 'Số lượng phụ tùng', 'nhom': 'Nhóm phụ tùng'},
        color_discrete_sequence=px.colors.qualitative.Pastel,
        text='so_luong'
    )
    
    # Cải thiện hiển thị
    fig_bar.update_traces(textposition='outside')
    fig_bar.update_layout(
        xaxis_title=None,
        yaxis_title="Số lượng",
        showlegend=False
    )
    
    st.plotly_chart(fig_bar, use_container_width=True)

# Thêm mô tả giải thích
st.markdown("""
**Giải thích biểu đồ:**
- **Biểu đồ tròn (bên trái)**: Thể hiện tỷ lệ % phân bổ các nhóm phụ tùng
- **Biểu đồ cột (bên phải)**: Thể hiện số lượng phụ tùng cụ thể trong mỗi nhóm
""")

# Đặc trưng từng nhóm
st.write("### Đặc trưng trung bình từng nhóm")
group_stats = final_data.groupby('nhom').agg({
    'trung_binh_xuat': 'mean',
    'do_bien_dong': 'mean',
    'tan_suat': 'mean',
    'ti_le_thang_xuat': 'mean'
}).reset_index()

fig2 = px.bar(
    group_stats.melt(id_vars='nhom'), 
    x='nhom', 
    y='value', 
    color='variable',
    barmode='group',
    title='Đặc trưng trung bình các nhóm',
    labels={'value': 'Giá trị trung bình', 'variable': 'Chỉ số'},
    color_discrete_sequence=px.colors.qualitative.Set2
)
st.plotly_chart(fig2, use_container_width=True)

# Chiến lược quản lý
st.write("## Chiến lược quản lý theo nhóm")

strategies = {
    'Nhóm A - Nhu cầu cao': {
        'Đặc điểm': 'Tần suất bán cao, doanh số ổn định, độ biến động thấp',
        'Chiến lược': [
            'Dự trữ nhiều, điểm đặt hàng (ROP) cao',
            'Dự báo chi tiết theo tuần/tháng',
            'Theo dõi sát sao biến động',
            'Ưu tiên quản lý hàng ngày'
        ]
    },
    'Nhóm B - Mùa vụ': {
        'Đặc điểm': 'Doanh số biến động mạnh theo mùa, tần suất không đều',
        'Chiến lược': [
            'Dự báo có yếu tố thời vụ',
            'Tăng dự trữ trước mùa cao điểm',
            'Giảm tồn kho sau mùa',
            'Phân tích lịch sử theo mùa'
        ]
    },
    'Nhóm C - Cố định': {
        'Đặc điểm': 'Chu kỳ bán đều đặn, khoảng cách giữa các lần bán ổn định',
        'Chiến lược': [
            'Quản lý theo lịch bảo trì',
            'Đặt hàng theo chu kỳ cố định',
            'Phối hợp với bộ phận dịch vụ',
            'Dự báo dựa trên lịch thay thế'
        ]
    },
    'Nhóm D - Nhu cầu thấp': {
        'Đặc điểm': 'Bán ít, không đều đặn, doanh số thấp',
        'Chiến lược': [
            'Tồn kho tối thiểu',
            'Đặt hàng theo nhu cầu thực tế',
            'Có thể áp dụng mô hình "Just-in-Time"',
            'Đánh giá định kỳ để loại bỏ hàng tồn'
        ]
    }
}

selected_group = st.selectbox("Chọn nhóm để xem chiến lược", options=list(strategies.keys()))

st.write(f"### Chiến lược cho {selected_group}")
col1, col2 = st.columns(2)

with col1:
    st.write("**Đặc điểm:**")
    st.write(strategies[selected_group]['Đặc điểm'])
    
    st.write("**Chiến lược quản lý:**")
    for strategy in strategies[selected_group]['Chiến lược']:
        st.write(f"- {strategy}")

with col2:
    # Lọc dữ liệu nhóm được chọn
    group_data = final_data[final_data['nhom'] == selected_group]
    
    # Hiển thị top 10 phụ tùng tiêu biểu
    st.write("**Top 10 phụ tùng tiêu biểu:**")
    top_items = group_data.nlargest(10, 'trung_binh_xuat')[['ma_pt', 'ten_pt', 'trung_binh_xuat']]
    st.dataframe(
        top_items.style.format({'trung_binh_xuat': '{:.1f}'}),
        hide_index=True
    )

# Xuất dữ liệu phân nhóm
st.write("## Xuất dữ liệu phân nhóm")
if st.button("Xuất file Excel"):
    with pd.ExcelWriter('phan_nhom_phu_tung.xlsx') as writer:
        final_data.to_excel(writer, index=False)
    st.success("Đã xuất file thành công!")