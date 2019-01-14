# Imports

import socket, threading, base64, hashlib, pickle, os, sys, binascii, select, time, traceback, select, contextlib
from random import randint
from Crypto import Random
from Crypto.Cipher import AES
with contextlib.redirect_stdout(None): # Imports pygame without printing version to terminal
    from pygame import mixer

# Notes:

# Background = #36393F
# Foreground = #484B51

try:
    import tkinter as tk
    from tkinter import ttk
    from tkinter import messagebox
    from tkinter import filedialog
    import tkinter.scrolledtext as tkst
except:
    print("[!] tkinter module is not installed, install using cmd 'py -m pip install tkinter'")
    exit(0)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
BreakConnection = False

# Diffie-hellman key declerations
publicPrime = None
publicBase = None
privateKey = None
cipherKey = None
# Encryption declerations
initialAES = None
finalAES = None

# Class declerations

class UserCredentials:
    def __init__(self, username, password, createaccount):
        self.username = username
        self.password = password
        self.createaccount = createaccount

class AESCipher(object):
    def __init__(self, key):
        self.key = self.hasher(key)

    def hasher(self, password):
        salt = b'\xdfU\xc1\xdf\xf9\xb30\x96' # This is the default salt i am using for client and server side
        return (  hashlib.pbkdf2_hmac("sha256",password.encode("utf-8"), salt, 1000000)  )

    def encrypt(self, raw):
        b64 = base64.b64encode(raw.encode("utf-8")).decode("utf-8")
        raw = self.pad(b64)
        rawbytes = bytes(raw,"utf-8")
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(rawbytes))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        try:
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
        except ValueError:
            print("[!] ValueError Occured")
        Decrypted = cipher.decrypt(enc[AES.block_size:])
        unpadded = self.unpad(Decrypted).decode("utf-8")
        Decoded = base64.b64decode(unpadded).decode("utf-8")
        return Decoded
        #return base64.b64decode(self.unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')).decode("utf-8")

    def pad(self,s): # Pads the string so that it complys with the AES 16 byte block size
        return s + (AES.block_size - len(s) % AES.block_size) * chr(AES.block_size - len(s) % AES.block_size)

    def unpad(self, s): # Turns the 16 byte complyant string to a normal string
        return s[:-ord(s[len(s)-1:])]

# Functions

def getLocalIP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80)) # 8.8.8.8 is Googles DNS server; its an ip not going to change anytime
    except:
        s.connect(("1.1.1.1",80)) # Cloudflare DNS Resolver project IP, another host that won't change soon
    return s.getsockname()[0] # Returns the local ip of the internet facing NIC adapter (This makes sure the local ip of a virtual adapter is not taken)

def sendMessage(cipher, message):
    encMessage = cipher.encrypt(message)
    try:
        sock.send(encMessage)
    except ConnectionResetError:
        print("Message could not be sent")
        messagebox.showerror("Message could not be sent","The connection to the server has been reset")

def recvMessage(cipher, *args):
    try:
        if not args:
            receaved = sock.recv(30000)
        else:
            receaved = sock.recv(args[0])
    except OSError:
        print("[!] {}".format(str(sys.exc_info()[1])))
        return False
    receaved = receaved.decode("utf-8")
    decrypted = cipher.decrypt(receaved)
    if len(decrypted) > 128:
        print("Receaved encrypted:",decrypted[:128],"of length {}".format(len(decrypted))) # For Debugging
    else:
        print("Receaved encrypted:",decrypted) # For Debugging
    return (decrypted)

def DH():
    data = sock.recv(1024)
    data=data.decode("utf-8")
    data = data.split(" ")
    secret = randint(2**100, 2**150)
    sendkey = pow(int(data[0]), secret, int(data[1]))
    sock.send(bytes(str(sendkey),"utf-8"))
    key = pow(int(data[2]),int(secret),int(data[1]))
    return key

def DependancyDownloader(file, url):
    from urllib.request import urlopen
    data=urlopen(url).read()
    with open(file,"wb") as f:
        f.write(data)
    data="" # Stores a large amount of unnececary data in ram so it is cleared by this

class ProtonClient(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.container = tk.Frame(self)
        # Used to download the icon from a server if it doesn't already exist
        if not os.path.isfile("ProtonDark.ico"):
            DependancyDownloader("ProtonDark.ico","https://raw.githubusercontent.com/TheDarthMole/ProtonChat/master/ProtonDark.ico")
        if not os.path.isfile("Notification.mp3"):
            DependancyDownloader("Notification.mp3","https://raw.githubusercontent.com/TheDarthMole/ProtonChat/master/Notification.mp3")
        tk.Tk.iconbitmap(self, default="ProtonDark.ico")
        self.container.pack(side="top", fill="both", expand= False)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        self.frames = {}
        self.killThread = False

        for f in (StartConnect, MessagePage): # Add more pages in here to make them switchable
            frame = f(self.container, self)
            self.frames[f] = frame
            frame.grid(row=0, column=0, sticky="nesw")

        self.showFrame(StartConnect)

    def showFrame(self, cont, **kwargs):
        frame = self.frames[cont]
        frame.tkraise()
        if cont == StartConnect:
            if "Disconnect" in kwargs and kwargs["Disconnect"]: # If the first statement is false,
                frame.DisconnectButtonPress()                    # the 2nd statement wont get run, therefore it wont thorw an error
                frame.configInterface("disabled")
            self.geometry("235x300")
        elif cont == MessagePage:
            frame.StartThreaddedMessages() # Starts the threadding messaging manager
            frame.enterText.focus_set()
            frame.eventReturn("Enter")
            self.geometry("900x550")

class StartConnect(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.controller = controller
        self.connected = False
        self.loggedIn=False
        tk.Frame.config(self,width=200, height=300) # Can edit background colour here
        self.label_title = ttk.Label(self, text = "Enter the Address and Port")
        self.label_title.grid(row=0, columnspan=2, pady=10)
        self.label_title.config(font="Helvetica 10")

        self.style = ttk.Style()
        self.style.configure("ProtonStyle.TEntry", background = "#36393F")
        self.style.map("ProtonStyle.TEntry",
                            foreground=[("disabled","grey"),
                                        ("active","#484B51")],
                            background=[("disabled","grey"),
                                        ("active","#36393F")])

        self.label_address = ttk.Label(self, text="Address")
        self.label_port = ttk.Label(self, text="Port")
        self.default_address = tk.StringVar(self, "127.0.0.1") # Completely for time efficiency, delete after testing
        self.default_port = tk.StringVar(self, "65528")        # however could be used for a default Server
        self.entry_address = tk.Entry(self, textvariable = self.default_address) # textvariable = self.default_address used for testing, time effective
        self.entry_port = tk.Entry(self, textvariable = self.default_port)
        self.label_address.grid(row=1, pady=3)
        self.label_port.grid(row=2, pady=3)
        self.entry_address.grid(row=1, column=1, pady=3, padx=11)
        self.entry_port.grid(row=2, column=1, pady=3, padx=11)
        self.button_connect = ttk.Button(self, text="Connect", command=self.ConnectButtonPress)
        self.button_connect.grid(row=3, padx=7, pady=5)
        self.button_disconnect = ttk.Button(self, text="Disconnect", command=self.DisconnectButtonPress, state="disabled")
        self.button_disconnect.grid(row=3, column=1, columnspan=1)
        self.label_connIndicator = ttk.Label(self, text="Current Status: Disconnected\n")
        self.label_connIndicator.grid(row=4, columnspan=2)
        self.CheckVar = tk.IntVar(value=0)
        self.checkbox_createAccount = ttk.Checkbutton(self, text="Create new account", variable = self.CheckVar, state = "disabled")
        self.checkbox_createAccount.grid(row=5, columnspan=2)
        self.label_username = ttk.Label(self, text="Username")
        self.label_password = ttk.Label(self, text="Password")
        self.entry_username = ttk.Entry(self, state="disabled") # Disabled because you can't login before connecting
        self.entry_password = ttk.Entry(self, state="disabled", show="*")
        self.label_username.grid(row=6)
        self.label_password.grid(row=7)
        self.entry_username.grid(row=6, column=1, pady=3)
        self.entry_password.grid(row=7, column=1, pady=3)
        self.button_login = ttk.Button(self, text="Login", command= lambda: self.LoginButtonPress(controller), state="disabled")
        self.button_login.grid(columnspan=2, padx=5, pady=5)
        self.button_nextpage = ttk.Button(self, text="Next Page", state="disabled", command=lambda: controller.showFrame(MessagePage))
        self.button_nextpage.grid(columnspan=2, padx=5, pady=5)
        self.place(relx=0.5, rely=0.5, anchor="center")

    def DisconnectButtonPress(self):
        global sock
        sock.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.label_connIndicator.config(text="Current Status: Disconnected\n")
        self.entry_username.config(state="disabled")
        self.entry_password.config(state="disabled")
        self.checkbox_createAccount.config(state="disabled")
        self.button_disconnect.config(state="disabled")
        self.button_connect.config(state="normal")
        self.button_nextpage.config(state="disabled")
        self.button_login.config(state="disabled")
        self.controller.killThread = True

    def ConnectButtonPress(self):
        global sock
        address = self.entry_address.get()
        port = self.entry_port.get()
        try:
            continueconnect = False
            sock.connect((address, int(port))) # Connect to the server
            print("Connected!")
            continueconnect = True
        except socket.gaierror:
            messagebox.showerror("Failed to connect!","The ip or port is not valid")
            return
        except TimeoutError:
            messagebox.showerror("Failed to connect!","The connection was refused or the host did not respond")
            return
        except OSError as e:
            messagebox.showerror("Failed to connect!",e)
            return
        except ValueError:
            messagebox.showerror("Failed to connect!","You entered an incorrect port number (It has to be a number)")
            return
        finally:
            if not continueconnect:
                sock.close()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            global DiffieHellman
            global initialAES
            DiffieHellman = DH() # We have created a diffie-hellman key exchange here, used for initialAES encryption
            initialAES = AESCipher(hex(int(DiffieHellman))) # Setting the diffie-hellman key as the key for AES
            print(recvMessage(initialAES))
            self.label_connIndicator.config(text="Current Status: Connected!\n            Please Log in")
            self.entry_username.config(state="normal")
            self.entry_password.config(state="normal")
            self.checkbox_createAccount.config(state="normal")
            self.button_login.config(state="normal")
            self.button_disconnect.config(state="normal")
            self.button_connect.config(state="disabled")
        except ConnectionResetError:
            print("[x] Connection with",address+":"+str(port),"was actively closed")
            messagebox.showerror("Connection lost!",("Connection with "+address+":"+str(port)+" was actively closed."))
            sock.close()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except ValueError:
            messagebox.showerror("Connected to wrong server!","You have connected to a server that is not running Proton Server.")
            sock.close()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def configInterface(self, value):
        for x in (self.entry_username, self.entry_password,self.checkbox_createAccount,self.button_login, self.button_disconnect, self.button_nextpage):
            x.config(state=value)
        if value == "disabled":
            self.button_login.config(state="active")
        else:
            self.button_login.config(state="disabled")

    def LoginButtonPress(self, controller):
        username = self.entry_username.get()
        password = self.entry_password.get()
        password = initialAES.hasher(password).hex()
        createaccount = self.CheckVar.get()
        tosend = UserCredentials(username,password,True if createaccount else False)
        self.UserCredentials = tosend
        tosend = pickle.dumps(tosend).hex() # Turns the class into bytes, therefore sendable over Sockets
        sendMessage(initialAES,tosend) # Sends the UserCredentials class pickled, hexified then encrypted to server
        self.loggedIn=False

        message = recvMessage(initialAES)
        if message[:3] == "ASC":
            self.loggedIn = True
            messagebox.showinfo("Account Created","You have successfully created an account!")
            self.button_login.config(state="disabled")
            self.button_nextpage.config(state="active")
            controller.showFrame(MessagePage)
        elif message[:3] == "SLI":
            self.loggedIn = True
            messagebox.showinfo("Login Successful","You have successfully logged in!")
            self.button_login.config(state="disabled")
            self.button_nextpage.config(state="active")
            controller.showFrame(MessagePage)
        elif message[:3] == "ERR":
            messagebox.showerror("An error occured", message[4:])
        elif message[:3] == "LAE":
            self.configInterface("disabled")
            self.DisconnectButtonPress()
            messagebox.showerror("Login credentials rejected","You have entered incorrect credentials too many times.")

class MessagePage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        parent.focus_set()
        self.parent = parent
        self.controller=controller
        self.grid_columnconfigure(0,weight=1)
        self.grid_rowconfigure(0,weight=1)
        self.uiMessages = tkst.ScrolledText(self, state="disabled", height=128)
        self.enterText = tk.Text(self, width=32, height=2)
        self.backButton = ttk.Button(self, text="Back", command=self.returnButton)
        self.sendButton = ttk.Button(self, text="Send", command=self.eventReturn)
        self.uploadButton = ttk.Button(self, text="Upload", command = lambda: self.upload())
        self.uiMessages.grid(row=0, sticky="NESW", columnspan=2)
        self.enterText.grid(row=1, column=0,sticky="NESW")
        self.backButton.grid(row=2, column=0, sticky="WS")
        self.sendButton.grid(row=1, column=1,sticky="E")
        self.uploadButton.grid(row=2, column=0, sticky="ES")
        self.sendingFiles = False
        self.onScreen = False
        self.threadStarted = False
        self.addAdminMessage("Welcome to Proton Messenger, use '/Help' for commands","Server") # Welcome message
        controller.bind("<Return>",self.eventReturn)

    def StartThreaddedMessages(self, *char):
        if not self.threadStarted:
            self.onScreen=True
            self.threadStarted = True
            self.MessageThread = threading.Thread(target=self.FetchMessages)
            self.MessageThread.daemon=True
            self.MessageThread.start()
            print("Another thread started!")

    def SwitcherMSG(self,*args):
        todisplay = args[0].split("|")
        if todisplay[2] == "Standard":
            self.addMessage("|".join(todisplay[3:]),todisplay[1])
        else:
            self.addAdminMessage("|".join(todisplay[3:]),todisplay[1])

    def SwitcherFileNotFound(self, *args):
        self.addAdminMessage("The file was not found","Server")

    def KeyError(self, *args):
        data = args[0].split("|")
        self.addAdminMessage("{} is not a valid command".format(" ".join(data[1:])), "Server")

    def FetchMessages(self):
        self.unbind("<Enter>")
        self.switcher = {
        "Msg": self.SwitcherMSG,
        "Filedownload": self.download,
        "Fnf": self.SwitcherFileNotFound,
        "Keyerror": self.KeyError,
        "Logout": self.logout}
        ready = select.select([sock], [], [], 5)
        print("FetchMessages running")
        import time
        while 1:
            if self.controller.killThread:
                self.controller.killThread = False
                self.threadStarted = False
                return
            if not self.sendingFiles:
                if ready[0]:
                    data = recvMessage(initialAES)
                    if type(data) == type(False) and data == False:
                        self.controller.killThread = False
                        self.threadStarted = False
                        return # If the data couldn't be collected because the socket is closed
                    data1 = data.split("|")
                    command = data1[0].title()
                    if command in self.switcher:
                        self.switcher[command](data)
                    else:
                        self.addAdminMessage("'{}' is not a valid command".format(command), "Server")
                else:
                    print("Not ready")

    def upload(self, *args):
        self.sendingFiles = True
        print("Uploading data!")
        filepath = filedialog.askopenfilename(title = "Select a file to upload",filetypes = (("All Files","*.*"),))
        if not filepath:
            self.addAdminMessage("No file was selected","Server")
            self.sendingFiles = False
            return
        filename = filepath.split("/")
        filename = filename[-1]
        if os.path.isfile(filepath):
            print("Sending '{}' to Server".format(filename))
            with open(filepath,"rb") as f:
                encDataToSend = binascii.hexlify(f.read(os.path.getsize(filepath))).decode("utf-8")
                encDataToSend = initialAES.encrypt(encDataToSend)
            sendMessage(initialAES,"Uploading|{}|{}".format(filename,str(len(encDataToSend))))
            fileOnServer = recvMessage(initialAES)
            if fileOnServer == "FAE":
                print("File is already on the server")
                self.addAdminMessage("A file by that name already exists on the server!","Server")
                self.sendingFiles=False
                return

            time.sleep(1)
            sock.send(encDataToSend)
            print("Sent file!")
            self.addAdminMessage("File uploaded to server","Server")
        else:
            print("File is not there!")
            self.addAdminMessage("You did not select a valid file!","Server")
            sendMessage(initialAES,"FNF")
        self.sendingFiles = False

    def download(self, data):
        self.sendingFiles = True
        print("Downloading data!")
        split = data.split("|")
        filename = split[1]
        print("Started download of {}".format(filename))
        self.addAdminMessage("Downloading '{}''".format(filename),"Server")
        filesize = int(split[2])
        f = open("new_"+filename,"wb")
        data = recvMessage(initialAES)
        encrypted = recvMessage(initialAES,int(data))
        decoded = binascii.unhexlify(encrypted)
        f.write(decoded)
        print("Done downloading!")
        self.addAdminMessage("Downloaded '{}' as 'new_{}'".format(filename, filename),"Server")
        self.sendingFiles = False

    def eventReturn(self, *event):
        #print("Return pressed", repr(event.char))
        if app.frames[StartConnect].loggedIn:
            text = self.enterText.get("1.0","end")
            text = text.rstrip("\n")
            self.enterText.delete("1.0", "end")
            if not text:
                return
            if text and text[0] == "/": # 'If text' is a quick check to see if there is data to manipulate
                tosend = text.split(" ")
                last = text.lstrip(tosend[0])
                last = last.lstrip(" ")
                sendMessage(initialAES, tosend[0]+"|"+last)
            else:
                sendMessage(initialAES, "MSG|"+text)
        else:
            app.frames[StartConnect].LoginButtonPress(self.controller)
    def logout(self,*args):
        self.controller.showFrame(StartConnect,Disconnect=True)

    def NotificationSound(self):
        mixer.init()
        mixer.music.load("Notification.mp3")
        mixer.music.play()
    def returnButton(self):
        self.onScreen = False
        self.controller.showFrame(StartConnect)
    def addText(self, text): # Adds text to the end of the scrollable text
        self.uiMessages.config(state="normal")
        self.uiMessages.insert("end",chars=str(text)+"\n")
        self.uiMessages.config(state="disabled")
    def addMessage(self, text, recipient):
        self.NotificationSound()
        self.uiMessages.config(state="normal")
        self.uiMessages.insert("end",chars=str("["+recipient+"] ")+str(text)+"\n")
        lastLine = int(self.uiMessages.index('end-1c').split('.')[0]) - 1
        self.uiMessages.tag_add("red", str(lastLine - len(text.splitlines())+1)+".0",str(lastLine - len(text.splitlines())+1)+"."+str(len(recipient)+2))
        self.uiMessages.tag_config("red", foreground = "red")
        self.uiMessages.see("end")
        self.uiMessages.config(state="disabled")
    def addAdminMessage(self, text, recipient):
        self.NotificationSound()
        self.uiMessages.config(state="normal")
        self.uiMessages.insert("end",chars=str("["+recipient+"] ")+str(text)+"\n")
        if len(text.splitlines())>1:
            lastLine = int(self.uiMessages.index('end-1c').split('.')[0]) - 2
        else:
            lastLine = int(self.uiMessages.index('end-1c').split('.')[0]) - 1
        self.uiMessages.tag_add("blue", str(lastLine - len(text.splitlines())+1)+".0",str(lastLine - len(text.splitlines())+1)+"."+str(len(recipient)+2))
        self.uiMessages.tag_config("blue", foreground = "blue")
        self.uiMessages.see("end")
        self.uiMessages.config(state="disabled")
    def addOwnMessage(self, text, recipient):
        pass

if __name__ == "__main__":
    try:
        app = ProtonClient()
        app.title("Proton Client")
    #    app.config(bg="#36393E")
        app.mainloop()
    except KeyboardInterrupt:
        print("KeyboardInterrupt occured, quitting")
    finally:
        sock.close()
