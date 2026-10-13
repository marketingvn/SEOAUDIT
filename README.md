# An Phước Realty — SEO Audit

Tự động kiểm tra SEO kỹ thuật trên các URL công khai của https://anphuocrealty.vn, theo dõi backlink đã khai báo và xuất báo cáo CSV/JSON.

## Chạy trên GitHub

Vào **Actions → An Phuoc SEO Audit → Run workflow**. Khi chạy xong, tải `seo-audit-reports` từ mục Artifacts.

Workflow chạy hằng ngày lúc **09:00 giờ Việt Nam** (`02:00 UTC`); thời điểm chạy thực tế có thể trễ. Không cần API key.

## Cấu hình

- `data/target_urls.csv`: danh sách URL cần kiểm tra (cột `url`).
- `data/backlinks.csv`: backlink đã đăng (cột `source_url,target_url`). Hiện để trống và **không tự tạo backlink**.
- Mỗi lần chạy xuất `reports/technical_audit.csv`, `reports/backlink_audit.csv` và `reports/summary.json`.

Không đặt thông tin đăng nhập WordPress vào mã nguồn. Bộ audit kiểm tra HTML nhận từ server, không render JavaScript; cảnh báo cần được xác minh trước khi chỉnh sửa website. Công cụ không ghi/sửa nội dung website WordPress.
