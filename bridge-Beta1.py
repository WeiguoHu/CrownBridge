from socket import *
import threading
import time
import re

mapArray = {
    "fader" : {
        "objFormated" : "0F16",
        "paramFormated" : "0003",
        "dataType" : "01"
    },
    "mute" : {
        "objFormated" : "0F16",
        "paramFormated" : "0006",
        "dataType" : "01"
    }
}

udp  = socket(AF_INET,SOCK_DGRAM)
udp.bind(('',3804))
udp.setsockopt(SOL_SOCKET,SO_BROADCAST,1)
addr = ('<broadcast>',3804)
addrArray = []

appIp = input("Please input server IP: ")
appPort = int(input("Please input server port: "))
app_tcp = socket(AF_INET, SOCK_STREAM)
app_tcp.connect((appIp, appPort))

IsRuning1 = True
IsRuning2 = True
discoAll = b"\x02\x19\x00\x00\x00\x48\x00\x33\x00\x00\x00\x00\xFF\xFF\x00\x00\x00\x00\x00\x00\x00\x20\x05\x00\x00\x00\x01\x01\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\xD4\xC4\x58\x46\x2C\x00\x10\x00\x00\x27\x10\x01\x04\xD4\xC4\x58\x46\x2C\x01\xC0\xA8\x02\xFD\xFF\xFF\xFF\x00\x00\x00\x00\x00"

def sendUdp(udp_socket):
    udp.sendto(discoAll,addr)

def recvUdp(udp_socket):
    while True:
        data,senderAddr = udp.recvfrom(1024)
        ipAddr,port = senderAddr
        if ipAddr != appIp:
            data = data.hex()
            header = parseHeader(data)
            hiq = header["sourceHiq"]
            target = [hiq,ipAddr]
            if not insertAddr(target,addrArray):
                break

def connectTcp(addrArray):
    for i in range(len(addrArray)):
        ipAddr = addrArray[i][1]
        tcp = "amp_tcp_" + str(i)
        addrArray[i].append({tcp:socket(AF_INET, SOCK_STREAM)})
        addrArray[i][2][tcp].connect((ipAddr, 3804))

def send_app(app_tcp):
    global IsRuning1
    while IsRuning1:
        send_app = input('请输入要发送到1的内容\n')
        app_tcp.send(send_app.encode('utf-8'))
        if send_app == "exit":
            IsRuning1 = False

def rece_app(app_tcp):
    global IsRuning1
    while IsRuning1:
        recv_msg = app_tcp.recv(1024).decode("utf8")
        if recv_msg == "exit":
            IsRuning1 = False
        print('从1接收到的信息为：%s\n' % recv_msg)
        dataArray = parseInput(recv_msg)
        if dataArray:
            sendArray = formatInput(dataArray)
            for i in sendArray:
                hiq = de2HeStr(dataArray["hiqId"])
                hiq = hiq.zfill(2)
                send2Amp(hiq,i)
                
def send_app_cus(msg):
    global IsRuning1
    if IsRuning1:
        app_tcp.send(msg.encode('utf-8'))

def send2Amp(hiq,msg):
    global addrArray
    if exist(hiq,addrArray):
        index = exist(hiq,addrArray)
        tcpIndex = "amp_tcp_" + str(index)
        tcpObj = addrArray[int(index)][2][tcpIndex]
        tcpObj.send(msg)

def sendDisco(msg):
    global IsRuning1
    while IsRuning1:
        for i in addrArray:
            for k,v in i[2].items():
                v.send(msg) 
                time.sleep(5)

def rece_amp(amp_tcp):
    global IsRuning2
    while IsRuning2:
        recv_msg2 = amp_tcp.recv(1024)
        recv_hex = recv_msg2.hex()
        header = parseHeader(recv_hex)
        bodySize = header["bodySize"]
        msgId = header["msgId"]
        desHiq = header["desHiq"]
        try:
            bodySizeHex = int(bodySize,16)
            msgId = int(msgId,16)
        except:
            print("number erro")
        if bodySizeHex <73:
            if msgId == 0:
                sendmsg = "Hiq " + desHiq + " send disco info"
                send_app_cus(sendmsg)
            else:
                sendmsg = parseHiq(recv_hex)
                send_app_cus(sendmsg)

def parseHeader(msg):
    header = {
        "ver":msg[0:2],
        "headerSize":msg[2:4],
        "bodySize":msg[10:12],
        "sourceHiq":msg[14:16],
        "sourceObjAdd":msg[18:22],
        "sourceChannel":msg[22:24],
        "desHiq":msg[26:28],
        "desObjAdd":msg[30:34],
        "channel":msg[34:36],
        "msgId":msg[36:40],
        "flg":msg[40:44],
        "hop":msg[44:46],
        "seqNum":msg[46:50]
        }
    return header

def parseHiq(msg):
    header = parseHeader(msg)
    msgId = header["msgId"]
    flg = header["flg"]
    if msgId == "0103" and flg == "0020":
        result = parseGet(msg)
    elif msgId == "0103" and flg == "0024":
        result = parseGetInfo(msg)
    return result
        
def parseGet(msg):
    header = parseHeader(msg)
    Hiq = header["sourceHiq"]
    Obj = header["sourceObjAdd"]
    channel = header["sourceChannel"]
    msg = msg[50:]
    numParam = msg[0:4]
    try:
        numParamHex = int(numParam,16)
    except:
        print("number erro")
    index = 8
    result = ""
    for i in range(numParamHex-1):
        result += "Hiq: " + Hiq + " obj: " + Obj + " on channel: " + channel + "\n" + "param: " + msg[index:(index+4)] + " = " + msg[(index+4):(index+8)] + "\n"
        index += 4
    return result

def parseGetInfo(msg):
    header = parseHeader(msg)
    Hiq = header["sourceHiq"]
    Obj = header["sourceObjAdd"]
    channel = header["sourceChannel"]
    msg = msg[50:]
    numParam = msg[0:4]
    try:
        numParamHex = int(numParam,16)
    except:
        print("number erro")
    index = 12
    result = ""
    for i in range(numParamHex-1):
        result += "Hiq: " + Hiq + " obj: " + Obj + " on channel: " + channel + "\n" + "param: " + msg[index:(index+4)] + " = " + msg[(index+6):(index+8)] + "\n"
        index += 8
    return result

def creDisco(hiq):
    disco = b"\x02\x19\x00\x00\x00\x48\x00\x33\x00\x00\x00\x00\x00\xFF\x00\x00\x00\x00\x00\x00\x00\x20\x05\x00\x00\x00\x01\x01\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\xD4\xC4\x58\x46\x2C\x00\x10\x00\x00\x27\x10\x01\x04\xD4\xC4\x58\x46\x2C\x01\xC0\xA8\x02\xFD\xFF\xFF\xFF\x00\x00\x00\x00\x00"
    disco = disco.hex()
    disco = disco[:26] + hiq + disco[28:]
    disco = bytes.fromhex(disco)
    return disco

def creHeader(desHiq,desObjAdd,channel,numParam,msgId):
    result = "02190000000000330000000000" + desHiq + "00" + desObjAdd + channel + msgId + "0020050000"
    return result

def creMultiGet(desHiq,desObjAdd,channel,numParam,param):
    msgId = "0103"
    header = creHeader(desHiq,desObjAdd,channel,numParam,msgId)
    numParam = numParam + 1
    numParamHex = de2HeStr(numParam)
    numParamHex = numParamHex.zfill(4)
    result = "0000" + param
    payload = numParamHex + result
    result = header + payload
    bodySize = int(len(result)/2)
    bodySizeHex = de2HeStr(bodySize)
    bodySizeHex = bodySizeHex.zfill(4)
    result = result[:8] + bodySizeHex + result [12:]
    return result

def creMultiSet(desHiq,desObjAdd,channel,numParam,param,dataType,value):
    msgId = "0100"
    header = creHeader(desHiq,desObjAdd,channel,numParam,msgId)
    numParamHex = de2HeStr(numParam)
    numParamHex = numParamHex.zfill(4)
    result = ""
    for i in range(numParam):
        result += param
        result += dataType
        result += value
    payload = numParamHex + result
    result = header + payload
    bodySize = int(len(result)/2)
    bodySizeHex = de2HeStr(bodySize)
    bodySizeHex = bodySizeHex.zfill(4)
    result = result[:8] + bodySizeHex + result [12:]
    return result

def de2HeStr(decimal):
    string = str(hex(decimal))
    string = string[2:]
    return string

def exist(target,array):
    for i in array:
        if target in i:
            return str(array.index(i))
    return False

def insertAddr(target,array):
    if not exist(target[1],array):
        array.append(target)
    else:
        return False
    #print(array)

def parseHeader(msg):
    header = {
        "ver":msg[0:2],
        "headerSize":msg[2:4],
        "bodySize":msg[10:12],
        "sourceHiq":msg[14:16],
        "sourceObjAdd":msg[18:22],
        "sourceChannel":msg[22:24],
        "desHiq":msg[26:28],
        "desObjAdd":msg[30:34],
        "channel":msg[34:36],
        "msgId":msg[36:40],
        "flg":msg[40:44],
        "hop":msg[44:46],
        "seqNum":msg[46:50]
        }
    return header

def parseInput(input):
    data = re.match(r"(^hiq (\d*))(( (get) (fader|mute) ([1-8]))+$|( (set) (fader|mute) ([1-8]) value (\d*))+$)", input)
    if data:
        print("match")
        head = data.group(1)
        hiqId = data.group(2)
        target = data.group()
        headnum = len(head)+1
        targetCut = target[headnum:]
        matchObj = re.match(r"(\w*).*?",targetCut)
        msgId = matchObj.group(1)
        numParam = target.count(msgId)
        resultArray = {
                "hiqId" : int(hiqId),
                "msgId" : msgId,
                "numParam" : numParam
            }
        if msgId == "set":
            for i in range(numParam):
                targetCut = targetCut[4:]
                result = re.match(r"(\w*) (\d) value (\d*)",targetCut)
                matchstr = result.group()
                lenth = len(matchstr)+1
                resultArray[i] = {
                    "obj" : result.group(1),
                    "channel" : int(result.group(2)),
                    "value" : int(result.group(3))
                }
                targetCut = targetCut[lenth:]
        elif msgId == "get":
            for i in range(numParam):
                targetCut = targetCut[4:]
                result = re.match(r"(\w*) (\d)",targetCut)
                matchstr = result.group()
                lenth = len(matchstr)+1
                resultArray[i] = {
                    "obj" : result.group(1),
                    "channel" : int(result.group(2))
                }
                targetCut = targetCut[lenth:]
        return resultArray
    else:
        print("not match")

def formatInput(dataArray):
    hiqFormated = de2HeStr(dataArray["hiqId"])
    msgId = dataArray["msgId"]
    msgIdFormated = ""
    numParam = dataArray["numParam"]
    objFormated = ""
    paramFormated = {}
    if len(hiqFormated) < 2:
        hiqFormated = "0" + hiqFormated
    sendArray = []
    if msgId == "get": 
        msgIdFormated = "0103"
        for i in range(numParam):
            channelFormated = "0" + de2HeStr(dataArray[i]["channel"])
            obj = dataArray[i]["obj"]
            objFormated = mapArray[obj]["objFormated"]
            paramFormated = mapArray[obj]["paramFormated"]
            sendData = creMultiGet(hiqFormated,objFormated,channelFormated,1,paramFormated)
            sendHex = bytes.fromhex(sendData)
            sendArray.append(sendHex)
    elif msgId == "set":
        msgIdFormated = "0100"
        for i in range(numParam):
            channelFormated = "0" + de2HeStr(dataArray[i]["channel"])
            value = dataArray[i]["value"]
            valueFormated = de2HeStr(value)
            if len(valueFormated) < 2:
                valueFormated = "0" + valueFormated
            obj = dataArray[i]["obj"]
            objFormated = mapArray[obj]["objFormated"]
            paramFormated = mapArray[obj]["paramFormated"]
            dataType = mapArray[obj]["dataType"]
            sendData = creMultiSet(hiqFormated,objFormated,channelFormated,1,paramFormated,dataType,valueFormated)
            sendHex = bytes.fromhex(sendData)
            sendArray.append(sendHex)
    return sendArray

def main():
    sendUdp(udp)
    recvUdp(udp)
    connectTcp(addrArray)
    threading.Thread(target=send_app, args=(app_tcp,)).start()
    threading.Thread(target=rece_app, args=(app_tcp,)).start()
    for infoArray in addrArray:
            hiq = infoArray[0]
            disco = creDisco(hiq)
            threading.Thread(target=sendDisco, args=(disco,)).start()
            for k,v in infoArray[2].items():
                threading.Thread(target=rece_amp, args=(v,)).start()

if __name__ == "__main__":
    main()