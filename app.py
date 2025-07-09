import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_loader import load_inventory_data

# Cấu hình trang
st.set_page_config(page_title="Phân tích kho phụ tùng", layout="wide")

# Tiêu đề ứng dụng
st.title("Phân tích dữ liệu kho phụ tùng xe")
st.subheader("Phân tích và so sánh hiệu quả hoạt động các kho")

# 1. Load dữ liệu
@st.cache_data
def load_data():
    try:
        # Sử dụng hàm load_inventory_data từ utils
        dmvt, ddh, px, pn, ro = load_inventory_data("data/du_lieu_phu_tung_thuc_te.xlsx")
        
        # Chuẩn hóa tên cột
        px = px.rename(columns={'Mã đơn hàng': 'Mã đơn hàng'})
        dmvt = dmvt.rename(columns={'Mã phụ tùng': 'Ma_phu_tung', 'Tên phụ tùng': 'Ten_phu_tung'})
        pn = pn.rename(columns={'Kho nhập': 'Kho_nhap', 'Số lượng nhập': 'So_luong_nhap'})
        px = px.rename(columns={'Kho xuất': 'Kho_xuat', 'Số lượng xuất': 'So_luong_xuat'})
        
        return dmvt, ddh, px, pn, ro
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu: {str(e)}")
        return None, None, None, None, None

# Load dữ liệu
with st.spinner('Đang tải dữ liệu...'):
    danh_muc, don_dat_hang, phieu_xuat, phieu_nhap, ro = load_data()

if danh_muc is None:
    st.stop()

# 2. Phân tích các kho - Phiên bản nâng cao
st.header("Phân tích hiệu quả các kho")

# Tạo tab phân tích
tab1, tab2, tab3, tab4 = st.tabs([
    "Tổng quan kho", 
    "Luồng hàng kho", 
    "So sánh kho", 
    "Cảnh báo"
])

with tab1:
    st.subheader("Tổng quan tình trạng các kho")
    
    # Tạo 2 cột
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Tính toán số liệu tổng quan
        tong_nhap = phieu_nhap.groupby('Kho_nhap')['So_luong_nhap'].sum().reset_index()
        tong_xuat = phieu_xuat.groupby('Kho_xuat')['So_luong_xuat'].sum().reset_index()
        
        # Merge dữ liệu
        tong_hop = pd.merge(
            tong_nhap, 
            tong_xuat, 
            left_on='Kho_nhap', 
            right_on='Kho_xuat', 
            how='outer'
        )
        tong_hop.columns = ['Kho', 'Tong_nhap', 'Kho_xuat', 'Tong_xuat']
        tong_hop = tong_hop[['Kho', 'Tong_nhap', 'Tong_xuat']]
        tong_hop['Ton_kho'] = tong_hop['Tong_nhap'] - tong_hop['Tong_xuat']
        tong_hop['Ti_le_xuat_nhap'] = tong_hop['Tong_xuat'] / tong_hop['Tong_nhap']
        
        # Hiển thị bảng với định dạng đẹp
        st.dataframe(
            tong_hop.style
                .format({
                    'Tong_nhap': '{:,.0f}',
                    'Tong_xuat': '{:,.0f}',
                    'Ton_kho': '{:,.0f}',
                    'Ti_le_xuat_nhap': '{:.2%}'
                })
                .bar(color='#5fba7d', subset=['Tong_nhap'])
                .bar(color='#d65f5f', subset=['Tong_xuat'])
                .background_gradient(cmap='Blues', subset=['Ton_kho']),
            use_container_width=True
        )
    
    with col2:
        # Hiển thị KPI tổng quan
        st.metric("Tổng số kho", len(tong_hop))
        st.metric("Tổng lượng nhập", f"{tong_hop['Tong_nhap'].sum():,.0f}")
        st.metric("Tổng lượng xuất", f"{tong_hop['Tong_xuat'].sum():,.0f}")
        st.metric("Tổng tồn kho", f"{tong_hop['Ton_kho'].sum():,.0f}")
        
        # Chọn kho để xem chi tiết
        selected_warehouse = st.selectbox(
            "Chọn kho xem chi tiết",
            options=tong_hop['Kho'].unique()
        )
        
        if selected_warehouse:
            kho_data = tong_hop[tong_hop['Kho'] == selected_warehouse].iloc[0]
            st.write(f"**Chi tiết kho {selected_warehouse}**")
            st.write(f"- Tổng nhập: {kho_data['Tong_nhap']:,.0f}")
            st.write(f"- Tổng xuất: {kho_data['Tong_xuat']:,.0f}")
            st.write(f"- Tồn kho: {kho_data['Ton_kho']:,.0f}")
            st.write(f"- Tỷ lệ xuất/nhập: {kho_data['Ti_le_xuat_nhap']:.2%}")

with tab2:
    st.subheader("Luồng hàng qua các kho theo thời gian")
    
    # Tùy chọn phân tích theo
    analysis_option = st.radio(
        "Phân tích theo",
        options=['Theo tháng', 'Theo quý', 'Theo năm'],
        horizontal=True
    )
    
    # Chuẩn bị dữ liệu theo khoảng thời gian
    if analysis_option == 'Theo tháng':
        phieu_nhap['Thoi_gian'] = phieu_nhap['Ngày nhập kho'].dt.to_period('M').astype(str)
        phieu_xuat['Thoi_gian'] = phieu_xuat['Ngày xuất hàng'].dt.to_period('M').astype(str)
    elif analysis_option == 'Theo quý':
        phieu_nhap['Thoi_gian'] = phieu_nhap['Ngày nhập kho'].dt.to_period('Q').astype(str)
        phieu_xuat['Thoi_gian'] = phieu_xuat['Ngày xuất hàng'].dt.to_period('Q').astype(str)
    else:
        phieu_nhap['Thoi_gian'] = phieu_nhap['Ngày nhập kho'].dt.to_period('Y').astype(str)
        phieu_xuat['Thoi_gian'] = phieu_xuat['Ngày xuất hàng'].dt.to_period('Y').astype(str)
    
    # Tính toán dữ liệu
    nhap_theo_tg = phieu_nhap.groupby(['Thoi_gian', 'Kho_nhap'])['So_luong_nhap'].sum().reset_index()
    xuat_theo_tg = phieu_xuat.groupby(['Thoi_gian', 'Kho_xuat'])['So_luong_xuat'].sum().reset_index()
    
    # Vẽ biểu đồ
    fig1 = px.line(
        nhap_theo_tg, 
        x='Thoi_gian', 
        y='So_luong_nhap', 
        color='Kho_nhap',
        title=f'Lượng nhập {analysis_option.lower()}',
        labels={'So_luong_nhap': 'Số lượng nhập', 'Thoi_gian': 'Thời gian'}
    )
    
    fig2 = px.line(
        xuat_theo_tg, 
        x='Thoi_gian', 
        y='So_luong_xuat', 
        color='Kho_xuat',
        title=f'Lượng xuất {analysis_option.lower()}',
        labels={'So_luong_xuat': 'Số lượng xuất', 'Thoi_gian': 'Thời gian'}
    )
    
    st.plotly_chart(fig1, use_container_width=True)
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.subheader("So sánh hiệu quả các kho")
    
    # Phân tích mặt hàng theo kho
    st.write("### Phân bổ mặt hàng theo kho")
    
    # Merge dữ liệu xuất với danh mục
    xuat_chi_tiet = pd.merge(
        phieu_xuat, 
        danh_muc, 
        left_on='Mã phụ tùng', 
        right_on='Ma_phu_tung', 
        how='left'
    )
    
    # Nhóm theo kho và phụ tùng
    kho_phu_tung = xuat_chi_tiet.groupby(['Kho_xuat', 'Ten_phu_tung'])['So_luong_xuat'].sum().reset_index()
    
    # Chọn kho để phân tích sâu
    kho_selected = st.selectbox(
        "Chọn kho để phân tích chi tiết", 
        options=kho_phu_tung['Kho_xuat'].unique(),
        key='warehouse_select'
    )
    
    if kho_selected:
     # Dữ liệu cho kho được chọn
        kho_data = kho_phu_tung[kho_phu_tung['Kho_xuat'] == kho_selected]
    
    # Top 10 mặt hàng xuất nhiều nhất
        top_items = kho_data.nlargest(10, 'So_luong_xuat').sort_values('So_luong_xuat', ascending=True)
    
        col1, col2 = st.columns(2)
    
        with col1:
            st.write(f"#### Top 10 mặt hàng xuất nhiều nhất - {kho_selected}")
            st.dataframe(
                top_items.style
                    .bar(color='#5fba7d', subset=['So_luong_xuat'])
                    .format({'So_luong_xuat': '{:,.0f}'}),
                use_container_width=True
            )
    
        with col2:
        # Tạo biểu đồ cột ngang
            fig = px.bar(
                top_items,
                x='So_luong_xuat',
                y='Ten_phu_tung',
                orientation='h',
                title=f"Top 10 mặt hàng xuất nhiều nhất - {kho_selected}",
                labels={'So_luong_xuat': 'Số lượng xuất', 'Ten_phu_tung': 'Tên phụ tùng'},
                color='So_luong_xuat',
                color_continuous_scale='Blues'
            )
        
        # Cải thiện giao diện biểu đồ
            fig.update_layout(
                yaxis={'categoryorder':'total ascending'},
                height=500,
                showlegend=False,
                margin=dict(l=100, r=50, b=50, t=50, pad=4)
            )
        
            st.plotly_chart(fig, use_container_width=True)
    
    # So sánh hiệu suất các kho
    st.write("### Chỉ số hiệu suất kho")

    # Tính toán các chỉ số quan trọng
    performance_metrics = phieu_nhap.groupby('Kho_nhap').agg({
        'So_luong_nhap': ['sum', 'mean', 'count']
    }).reset_index()
    performance_metrics.columns = ['Kho', 'Tong_nhap', 'Trung_binh_nhap', 'So_lan_nhap']

    # Tính thêm các chỉ số từ phiếu xuất
    xuat_metrics = phieu_xuat.groupby('Kho_xuat')['So_luong_xuat'].sum().reset_index()
    performance_metrics = pd.merge(
        performance_metrics,
        xuat_metrics,
        left_on='Kho',
        right_on='Kho_xuat',
        how='left'
    )
    performance_metrics['Ti_le_xuat_nhap'] = performance_metrics['So_luong_xuat'] / performance_metrics['Tong_nhap']
    performance_metrics['Ton_kho'] = performance_metrics['Tong_nhap'] - performance_metrics['So_luong_xuat']

    # Hiển thị các biểu đồ cột so sánh
    col1, col2 = st.columns(2)

    with col1:
        # Biểu đồ tổng nhập/xuất
        fig = px.bar(
            performance_metrics,
            x='Kho',
            y=['Tong_nhap', 'So_luong_xuat'],
            barmode='group',
            title='Tổng lượng nhập và xuất theo kho',
            labels={'value': 'Số lượng', 'variable': 'Loại'},
            color_discrete_sequence=['#1f77b4', '#ff7f0e']
        )
        fig.update_layout(yaxis_title='Số lượng')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Biểu đồ tồn kho
        fig = px.bar(
            performance_metrics,
            x='Kho',
            y='Ton_kho',
            title='Tồn kho hiện tại các kho',
            color='Ton_kho',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig, use_container_width=True)

    # Biểu đồ các chỉ số khác
    st.write("#### Các chỉ số hiệu suất khác")
    metrics_to_show = st.multiselect(
        'Chọn chỉ số để so sánh',
        options=['Trung_binh_nhap', 'So_lan_nhap', 'Ti_le_xuat_nhap'],
        default=['Trung_binh_nhap', 'Ti_le_xuat_nhap'],
        format_func=lambda x: {
            'Trung_binh_nhap': 'Lượng nhập trung bình',
            'So_lan_nhap': 'Số lần nhập kho',
            'Ti_le_xuat_nhap': 'Tỷ lệ xuất/nhập'
        }[x]
    )

    if metrics_to_show:
        fig = px.bar(
            performance_metrics,
            x='Kho',
            y=metrics_to_show,
            barmode='group',
            title='So sánh các chỉ số hiệu suất kho',
            labels={'value': 'Giá trị', 'variable': 'Chỉ số'}
        )
        # Đổi tên hiển thị cho legend
        for i, d in enumerate(fig.data):
            d.name = {
                'Trung_binh_nhap': 'Lượng nhập TB',
                'So_lan_nhap': 'Số lần nhập',
                'Ti_le_xuat_nhap': 'Tỷ lệ X/N'
            }.get(d.name, d.name)
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Cảnh báo kho")
    
    # Cảnh báo tồn kho thấp
    st.write("### Cảnh báo tồn kho thấp")
    
    # Tính tổng nhập theo kho và mã phụ tùng
    tong_nhap = phieu_nhap.groupby(['Kho_nhap', 'Mã phụ tùng'])['So_luong_nhap'].sum().reset_index()
    tong_nhap.columns = ['Kho', 'Ma_phu_tung', 'Tong_nhap']
    
    # Tính tổng xuất theo kho và mã phụ tùng
    tong_xuat = phieu_xuat.groupby(['Kho_xuat', 'Mã phụ tùng'])['So_luong_xuat'].sum().reset_index()
    tong_xuat.columns = ['Kho', 'Ma_phu_tung', 'Tong_xuat']
    
    # Merge và tính tồn kho
    ton_kho = pd.merge(
        tong_nhap,
        tong_xuat,
        on=['Kho', 'Ma_phu_tung'],
        how='outer'
    ).fillna(0)
    
    ton_kho['Ton_kho'] = ton_kho['Tong_nhap'] - ton_kho['Tong_xuat']
    
    # Merge với danh mục để lấy tên phụ tùng
    ton_kho = pd.merge(
        ton_kho,
        danh_muc[['Ma_phu_tung', 'Ten_phu_tung']],
        on='Ma_phu_tung',
        how='left'
    )
    
    # Lọc các mặt hàng tồn kho âm hoặc dưới ngưỡng
    ngưỡng_cảnh_báo = st.slider(
        "Ngưỡng cảnh báo tồn kho", 
        min_value=0,
        max_value=100,
        value=10
    )
    
    items_canh_bao = ton_kho[ton_kho['Ton_kho'] <= ngưỡng_cảnh_báo]
    
    if not items_canh_bao.empty:
        # Chỉ hiển thị các cột cần thiết
        st.dataframe(
            items_canh_bao[['Kho', 'Ma_phu_tung', 'Ten_phu_tung', 'Ton_kho']]
                .sort_values('Ton_kho')
                .style
                .applymap(lambda x: 'color: red' if x <= 0 else 'color: orange', subset=['Ton_kho']),
            use_container_width=True
        )
    else:
        st.success("Không có mặt hàng nào dưới ngưỡng cảnh báo")