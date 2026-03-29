import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.mime.image import MIMEImage
### get password https://myaccount.google.com/apppasswords
def send_email(subject, body, image_path):
    SMTP_SERVER = "smtp.gmail.com"  # สำหรับ Gmail
    SMTP_PORT = 587

    # สร้างข้อความอีเมล
    msg = MIMEMultipart("related")
    msg["From"] = "mild.mild5225@gmail.com"
    msg["To"] = "mild.mild5225@gmail.com"
    msg["Subject"] = subject

    # เนื้อหา HTML ที่ฝังภาพ (ใช้ `cid:image1` อ้างอิง)
    html = f"""
    <html>
    <body>
        <h2>{body}</h2>
        <img src="cid:image1">
    </body>
    </html>
    """
    msg.attach(MIMEText(html, "html"))

    # ฝังภาพในเนื้อหาอีเมล
    with open(image_path, "rb") as img_file:
        img = MIMEImage(img_file.read())
        img.add_header("Content-ID", "<image1>")  # ใช้ใน HTML
        msg.attach(img)

    # แนบไฟล์ภาพ (ให้ดาวน์โหลด)
    with open(image_path, "rb") as file:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={image_path}")
        msg.attach(part)

    # ส่งอีเมล
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        ### get password https://myaccount.google.com/apppasswords
        server.login("mild.mild5225@gmail.com", "wnhmdlanbowugmhz")
        server.sendmail("mild.mild5225@gmail.com", "mild.mild5225@gmail.com", msg.as_string())
        server.quit()
        print("✅ ส่งอีเมลสำเร็จ!")
    except Exception as e:
        print("❌ เกิดข้อผิดพลาด:", e)

