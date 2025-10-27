code = secret1234
password =  input("Enter the password: ")
while True:
    if len(password)!=len(code):
        print("Incorrect password length. Try again.")
    if len(password) == len(code) and password != code:
        print("Password length is correct.But the password is incorrect. Try again.")
    elif password == code:
        print("Access granted.")
        break
    else:
        print("Incorrect password. Try again.")

