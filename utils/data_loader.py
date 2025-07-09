# utils/data_loader.py
import pandas as pd
import logging

def load_inventory_data(file_path):
    """
    Tải dữ liệu từ file Excel gồm 5 sheet
    """
    try:
        # Đọc Danh mục vật tư
        dmvt = pd.read_excel(
            file_path,
            sheet_name='Danh_muc_vat_tu',
            usecols=['Mã phụ tùng', 'Tên phụ tùng', 'Group No', 'Part Name Code', 'Các model áp dụng']
        )

        # Đọc Đơn đặt hàng bán - ĐẢM BẢO CHUYỂN ĐỔI NGÀY THÁNG
        ddh = pd.read_excel(
            file_path,
            sheet_name='Don_dat_hang_ban',
            usecols=['Ngày đặt hàng', 'Mã đại lý', 'Mã đơn hàng', 'Mã phụ tùng', 'Số lượng', 'Hình thức đơn hàng']
        )
        ddh['Ngày đặt hàng'] = pd.to_datetime(ddh['Ngày đặt hàng'], errors='coerce')  # Thêm dòng này

        # Đọc Phiếu xuất - ĐẢM BẢO CHUYỂN ĐỔI NGÀY THÁNG
        px = pd.read_excel(
            file_path,
            sheet_name='Phieu_xuat',
            usecols=['Ngày xuất hàng', 'Mã đại lý', 'Mã đơn hàng', 'Số phiếu xuất', 'Mã phụ tùng', 'Số lượng xuất', 'Kho xuất']
        )
        px['Ngày xuất hàng'] = pd.to_datetime(px['Ngày xuất hàng'], errors='coerce')  # Thêm dòng này

        # Đọc Phiếu nhập - ĐẢM BẢO CHUYỂN ĐỔI NGÀY THÁNG
        pn = pd.read_excel(
            file_path,
            sheet_name='Phieu_nhap',
            usecols=['Ngày nhập kho', 'Mã phụ tùng', 'Số lượng nhập', 'Kho nhập']
        )
        pn['Ngày nhập kho'] = pd.to_datetime(pn['Ngày nhập kho'], errors='coerce')  # Thêm dòng này

        # Đọc RO - ĐẢM BẢO CHUYỂN ĐỔI NGÀY THÁNG
        ro = pd.read_excel(
            file_path,
            sheet_name='RO',
            usecols=['Ngày đặt RO', 'Mã đại lý', 'Mã phụ tùng', 'Số lượng']
        )
        ro['Ngày đặt RO'] = pd.to_datetime(ro['Ngày đặt RO'], errors='coerce')  # Thêm dòng này

        # Lọc bỏ các dòng có ngày tháng không hợp lệ
        ddh = ddh.dropna(subset=['Ngày đặt hàng'])
        px = px.dropna(subset=['Ngày xuất hàng'])
        pn = pn.dropna(subset=['Ngày nhập kho'])
        ro = ro.dropna(subset=['Ngày đặt RO'])

        return dmvt, ddh, px, pn, ro

    except Exception as e:
        logging.error(f"Lỗi tải dữ liệu: {str(e)}")
        raise