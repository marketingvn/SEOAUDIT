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

## Quét tự động toàn sitemap (đã bật)

Chương trình đọc `/sitemap.xml` và `/wp-sitemap.xml`, theo các sitemap con trong cùng tên miền, sau đó kiểm tra tối đa **150 URL HTML** trong một lần chạy (gồm các URL cấu hình thủ công). Có thể thay đổi giới hạn qua biến môi trường `SEO_MAX_PAGES` (tối đa 500).

Các báo cáo trong artifact:
- `technical_audit.csv`: tình trạng từng URL, title, meta, H1, canonical và cảnh báo.
- `seo_findings.md`: danh sách URL có cảnh báo để đọc nhanh.
- `summary.json`: số URL sitemap tìm được, số sitemap đọc, lỗi sitemap và tổng hợp audit.
- `backlink_audit.csv`: kiểm tra backlink đã khai báo; không phải công cụ tự tìm backlink.

**Lưu ý:** Chạy thử trên GitHub sau mỗi lần cập nhật. Đây là audit HTML nguồn, không thể khẳng định Google index hay không index nếu thiếu dữ liệu Search Console. Website dùng WordPress hay code riêng đều kiểm tra bằng URL công khai được.
