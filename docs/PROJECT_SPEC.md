# PROJECT_SPEC - MVP v0.1

## 1) Tieu de du an

**GeoQR Studio**

## 2) Nguoi dung muc tieu

- Nguoi dung can kiem tra toa do tu `GCN QSDD` hoac tai lieu lien quan.
- Nhu cau chinh: doi chieu nhanh vi tri toa do tren giay to dat dai voi vi tri thuc te tren ban do.

## 3) Use case chinh

1. Nguoi dung doc hoac nhap toa do VN2000 tu `GCN QSDD`.
2. Nguoi dung chon tinh/thanh pho ghi tren chung nhan.
3. He thong chuyen doi toa do dia chinh VN2000 sang WGS84 `Latitude/Longitude`.
4. Neu nguoi dung dong y, he thong lay GPS hien tai tu trinh duyet dien thoai.
5. He thong tinh khoang cach tu GPS hien tai den diem da chuyen doi.
6. He thong tao Google Maps URL va ma QR de mo nhanh.

## 4) Pham vi MVP v0.1

- Chi ho tro nhap toa do thu cong.
- Co chuc nang chon tinh/thanh pho.
- Tu dong suy ra CRS tu file cau hinh.
- Co canh bao kha nang dao `X/Y` hoac `E/N`.
- Lay GPS hien tai (neu duoc cap quyen trinh duyet).
- Tinh khoang cach den diem da chuyen doi.
- Tao Google Maps URL.
- Tao ma QR tu URL.
- Giao dien mobile-first, nhan dien GeoQR Studio.
- Khong OCR trong MVP v0.1.
- Khong database trong MVP v0.1.
- Khong Google Maps API trong MVP v0.1.

## 5) Ngoai pham vi MVP v0.1

- OCR doc anh tai lieu.
- Luu tru du lieu khach hang.
- Luu tru anh `GCN`.
- Tich hop Google Maps API nhung.
- Offline maps.
- Du lieu quy hoach.
- Ung dung native mobile.
- Quy trinh quan ly phan quyen nguoi dung.

## 6) Gia dinh dia chinh VN2000

- Du lieu nguon la toa do tu `GCN QSDD` hoac ban do dia chinh.
- Quy tac CRS mac dinh:
  - Datum: `VN-2000`
  - Phep chieu: `TM-3`
  - `k0 = 0.9999`
  - False easting = `500000`
  - False northing = `0`
  - Don vi = `meter`
- Kinh tuyen truc duoc suy ra theo cau hinh tinh/thanh pho.
- Nguoi dung khong duoc tu chon cac tham so CRS ky thuat.

## 7) Input UX

- Tinh/thanh pho theo `GCN`.
- Gia tri toa do 1.
- Gia tri toa do 2.
- Che do nhap:
  - a) Tu dong nhan dien
  - b) Gia tri 1 = Easting, Gia tri 2 = Northing
  - c) Gia tri 1 = Northing, Gia tri 2 = Easting

## 8) Output UX

- Latitude
- Longitude
- Khoang cach den GPS hien tai (neu co)
- Google Maps URL
- Ma QR
- Canh bao
- Nut copy

## 9) Branding

- Primary: `#005993`
- Accent: `#D71249`
- Light background: `#F4F8FB`
- Phong cach UI chuyen nghiep, ro rang.
- Neu co file `assets/brand/logo.png` thi su dung logo nay.

## 10) Luu y an toan/phap ly

- Ket qua chi phuc vu muc dich tham khao/ho tro noi bo.
- Ket qua khong thay the:
  - ket qua do dac chinh thuc,
  - xac nhan cua co quan dia chinh co tham quyen,
  - tham dinh phap ly (legal due diligence).

## 11) Kien truc ky thuat

- Backend: `FastAPI` (Python).
- Frontend: web mobile-first, huong PWA.
- Logic chuyen doi toa do duoc tach rieng khoi UI.
- CRS van hanh theo cau hinh (`config-driven CRS`).
- Co bo test doi chieu theo file tham chieu CSV (`tests/test_coordinates.csv`).

## 12) Tieu chi nghiem thu MVP v0.1

- Ung dung chay duoc tren moi truong local.
- Nguoi dung chon duoc tinh/thanh va nhap duoc toa do.
- API tra ve duoc: `lat/lng`, `maps URL`, `QR code`, `warnings`.
- Frontend lay duoc GPS hien tai neu nguoi dung cho phep.
- Hien thi duoc khoang cach.
- Test vuot qua bo du lieu `tests/test_coordinates.csv`.
