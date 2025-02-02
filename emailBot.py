import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def email(subject, body):
    sender_email = "vendingmachine.bot2000@gmail.com"
    receiver_email = "kowsari.kian@gmail.com"
    password = "aewa gtvq zfox kibz"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Encrypt the connection
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
            print("Email sent successfully!")
    except Exception as e:
        print(f"Error: {e}")
