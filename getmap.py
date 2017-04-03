'''
pygetmap:

Download web map by cooridinates

'''

#Longittude 经度
#Latitude   纬度
#Mecator x = y = [-20037508.3427892,20037508.3427892]
#Mecator Latitue = [-85.05112877980659，85.05112877980659]


from math import floor,pi,log,tan,atan,exp
import urllib.request as ur
import PIL.Image as pil
import io, asyncio

HEADERS = 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.76 Safari/537.36'

MAP_URLS={
"google":{"domain":"mt2.google.cn","url":"/vt/lyrs={style}&hl=zh-CN&gl=CN&src=app&x={x}&y={y}&z={z}"},
"amap":{"domain":"wprd02.is.autonavi.com","url":"/appmaptile?style={style}&x={x}&y={y}&z={z}"},
"tencent_s":{"domain":"p3.map.gtimg.com","url":"/sateTiles/{z}/{fx}/{fy}/{x}_{y}.jpg"},
"tencent_m":{"domain":"rt0.map.gtimg.com","url":"/tile?z={z}&x={x}&y={y}&styleid=3" }}

EXIT = False

def geturl(source,x,y,z,style):
    '''
    Get the picture url for download.
    style:
        m for map
        s for satellite
    source:
        goole or amap or tencent
    x y:
        google-style tile coordinate system
    z:
        zoom 
    '''
    if source == 'google':
        furl=MAP_URLS["google"]["url"].format(x=x,y=y,z=z,style=style)
    elif source == 'amap':
        style=6 if style=='s' else 7   # for amap 6 is satellite and 7 is map.
        furl=MAP_URLS["amap"]["url"].format(x=x,y=y,z=z,style=style)
    elif source == 'tencent':
        y=2**z-1-y
        if style == 's':
            furl=MAP_URLS["tencent_s"]["url"].format(x=x,y=y,z=z,fx=floor(x/16),fy=floor(y/16))
        else:
            furl=MAP_URLS["tencent_m"]["url"].format(x=x,y=y,z=z)
    else:
        raise Exception("Unknown Map Source ! ")

    return furl

def getdomain(source,style):
    if source == 'tencent':
        if style == "s":
            return MAP_URLS["tencent_s"]["domain"]
        else:
            return MAP_URLS["tencent_m"]["domain"]
    elif source == "amap" or source == "google":
        return MAP_URLS[source]["domain"]
    else:
        raise Exception("Unkonwn Map Source ! ")


#WGS-84经纬度转Web墨卡托
def wgs2macator(x,y):
    y = 85.0511287798 if y > 85.0511287798 else y
    y = -85.0511287798 if y < -85.0511287798 else y

    x2 = x * 20037508.34 / 180
    y2 = log(tan((90+y)*pi/360))/(pi/180)
    y2 = y2*20037508.34/180
    return x2, y2

#Web墨卡托转经纬度
def mecator2wgs(x,y):
    x2 = x / 20037508.34 * 180
    y2 = y / 20037508.34 * 180
    y2= 180/pi*(2*atan(exp(y2*pi/180))-pi/2)
    return x2,y2


'''
东经为正，西经为负。北纬为正，南纬为负
j经度 w纬度 z缩放比例[0-22] ,对于卫星图并不能取到最大，测试值是20最大，再大会返回404.
'''
# 根据WGS-84 的经纬度获取谷歌地图中的瓦片坐标
def getpos(j,w,z):
    '''
    Get google-style tile cooridinate from geographical coordinate
    j : Longittude
    w : Latitude
    z : zoom
    '''
    isnum=lambda x: isinstance(x,int) or isinstance(x,float)
    if not(isnum(j) and isnum(w)):
        raise TypeError("j and w must be int or float!")
        return None

    if not isinstance(z,int) or z<0 or z>22:
        raise TypeError("z must be int and between 0 to 22.")
        return None

    if j<0:
        j=180+j
    else:
        j+=180
    j/=360 # make j to (0,1)

    w=85.0511287798 if w>85.0511287798 else w
    w=-85.0511287798 if w<-85.0511287798 else w
    w=log(tan((90+w)*pi/360))/(pi/180)
    w/=180 # make w to (-1,1)
    w=1-(w+1)/2 # make w to (0,1) and left top is 0-point

    num=2**z
    x=floor(j*num)
    y=floor(w*num)
    return x,y


#根据瓦片坐标范围，获得该区域四个角的web墨卡托投影坐标
def getframeM(inx,iny,inx2,iny2,z):
    '''
    Get the frame of region 
    input lefttop and rightbutton tile cooridinates
    output WebMecator cooridinates of the frame
    '''
    length = 20037508.3427892
    sum=2**z
    LTx=inx / sum*length*2 - length
    LTy= -(iny / sum*length*2) + length

    RBx=(inx2+1) / sum*length*2 - length
    RBy= -((iny2+1) / sum*length*2) + length

    #LT=left top,RB=right buttom
    #返回四个角的投影坐标
    res={'LT':(LTx,LTy),'RB':(RBx,RBy),'LB':(LTx,RBy),'RT':(RBx,LTy)}
    return res

#根据瓦片坐标范围，获得该区域四个角的地理经纬度坐标
def getframeW(inx,iny,inx2,iny2,z):
    '''
    Get the frame of region 
    input lefttop and rightbutton tile cooridinates
    output geographical cooridinates of the frame
    '''
    zb=getframeM(inx,iny,inx2,iny2,z)
    for index,xy in zb.items():
        zb[index]=mecator2wgs(*xy)
    #返回四个角的经纬度坐标
    return zb

def printzb(zb):
    if not zb:
        return
    print("左上：({0:.7f},{1:.7f})".format(*zb['LT']))
    print("右上：({0:.7f},{1:.7f})".format(*zb['RT']))
    print("左下：({0:.7f},{1:.7f})".format(*zb['LB']))
    print("右下：({0:.7f},{1:.7f})".format(*zb['RB']))



async def async_getpic(domain, urls, out_pics, index, multiple):  # 通过协程来下载图像，更具效率
    length=len(urls)
    global EXIT
    for i in range(index,length,multiple):
        if EXIT:
            return
        connect = asyncio.open_connection(host=domain, port=80)
        try:
            reader, writer = await connect
        except:
            EXIT = True
            return
        header = 'GET {url} HTTP/1.0\r\nHost: {domain}\r\n{header}\r\n\r\n'.format(url=urls[i], 
            domain=domain, header=HEADERS)
        writer.write(header.encode('utf-8'))
        await writer.drain()
        msg = await reader.read()
        if msg.find(b"Content-Type: image")>1:
            pl=msg.find(b"\r\n\r\n")
            out_pics[i] = msg[pl+4:]
        else:
            out_pics[i] = None
            EXIT = True
        
        writer.close()


def async_getpics(urls,domain, multiple=10): # 根据urls列表下载图片数据
    loop = asyncio.get_event_loop()     # 得到一个事件循环模型
    minor_pics=[None for i in range(len(urls))] #预留list空间
    tasks=[]
    global EXIT
    EXIT = False
    for i in range(multiple):
        tasks.append(async_getpic(domain,urls,minor_pics,i,multiple))

    loop.run_until_complete(asyncio.wait(tasks))    # 执行任务
    loop.close()
    return minor_pics  # 返回图片数据


def getpic(x1,y1,x2,y2,z,source='google',outfile="MAP_OUT.png",style='s'):
    '''
    依次输入左上角的经度、纬度，右下角的经度、纬度，缩放级别，地图源，输出文件，影像类型（默认为卫星图）
    获取区域内的瓦片并自动拼合图像。
    '''
    pos1x, pos1y = getpos(x1, y1, z)
    pos2x, pos2y = getpos(x2, y2, z)
    frame=getframeW(pos1x,pos1y,pos2x,pos2y,z)
    lenx = pos2x - pos1x + 1
    leny = pos2y - pos1y + 1
    print("瓦片总数量：{x} X {y}".format(x=lenx,y=leny))

    domain = getdomain(source,style)
    urls=[geturl(source,i,j,z,style) for j in range(pos1y, pos1y + leny) for i in range(pos1x, pos1x + lenx)]
    print("正在下载......")
    datas = async_getpics(urls, domain)
    
    if EXIT:
        print("下载出错！\n可能是缩放级别z过大，或者未连接到网络。")
        return

    print("下载完成！\n开始拼合图像......") 
    outpic = pil.new('RGBA',(lenx*256,leny*256))
    for i,data in enumerate(datas):
        picio=io.BytesIO(data)
        try:
            small_pic=pil.open(picio)
        except:
            print(data)
        y,x = i // lenx,i % lenx
        outpic.paste(small_pic,(x*256,y*256))

    print('拼合完成！\n正在导出...')
    outpic.save(outfile)
    print('导出完成！')
    return frame


def getpic_s(x,y,z,source='google',outfile="out_single.png",style="s"):
    '''获得单幅瓦片图像'''
    getpic(x,y,x,y,z,source,outfile,style)


if __name__ == '__main__':
    #下载西安 青龙寺地块 卫星地图
    mm=getpic(108.9797845,34.2356831,108.9949663,34.2275018,
        18,source='google',style='s',outfile="myout.png")
    printzb(mm)
    
