import urllib.parse

# Thay đổi dòng dưới thành mật khẩu thật của bạn
your_password = "L@hao" 

encoded_password = urllib.parse.quote_plus(your_password)
print(encoded_password)