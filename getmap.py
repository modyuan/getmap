#get google map by coori
#Longittude 经度
#Latitude   纬度
#Mecator x = y = [-20037508.3427892,20037508.3427892]
#Mecator Latitue = [-85.05112877980659，85.05112877980659]


from math import floor,pi,log,tan,atan,exp
import urllib.request as ur
import PIL.Image as pil
import io

headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.76 Safari/537.36'}

google_url="http://mt2.google.cn/vt/lyrs={style}&hl=zh-CN&gl=CN&src=app&x={x}&y={y}&z={z}"
amap_url="http://wprd02.is.autonavi.com/appmaptile?style={style}&x={x}&y={y}&z={z}"


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
    isnum=lambda x: isinstance(x,int) or isinstance(x,float)
    if not(isnum(j) and isnum(w)):
        raise TypeError("j and w must be int or float!")
        return None

    if not isinstance(z,int) or z<0:
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
    zb=getframeM(inx,iny,inx2,iny2,z)
    for index,xy in zb.items():
        zb[index]=mecator2wgs(*xy)
    #返回四个角的经纬度坐标
    return zb

def printzb(zb):
    print("左上：({0:.7f},{1:.7f})".format(*zb['LT']))
    print("右上：({0:.7f},{1:.7f})".format(*zb['RT']))
    print("左下：({0:.7f},{1:.7f})".format(*zb['LB']))
    print("右下：({0:.7f},{1:.7f})".format(*zb['RB']))



# 根据瓦片坐标获取图像数据
def getdata(x,y,z,source,style='s'):
    '''
    根据瓦片坐标等获取谷歌地图的瓦片的下载地址。
    x y 瓦片坐标
    z   缩放级别
    style:
        s卫星图
        m路线图
    source:
        amap 高德
        google 谷歌
    '''
    if source=="amap":
        style=style.lower()
        style=6 if style=='s' else 7
        source=amap_url
    elif source == "google":
        source=google_url
    else:
        raise Exception("Unknown Map Source ! ")

    furl=source.format(x=x,y=y,z=z,style=style)
    req = ur.Request(url=furl, headers=headers) 
    try:
        data=ur.urlopen(req,timeout=5).read()
    except:
        print("get picture failed!")
        print("url:",furl)
        exit()
    return data


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
    print("总数量：{x} X {y}".format(x=lenx,y=leny))
    outpic=pil.new('RGBA',(lenx*256,leny*256))
    datas=[]
    for i in range(lenx):
        datas.append([])
        for j in range(leny):
            print("正在下载：{0},{1}".format(i,j))
            mapdata=getdata(pos1x+i,pos1y+j,z,source,style)
            datas[i].append(mapdata)

    print("下载完成！")
    picio=None
    print('开始拼合图像......')
    for x,sublist in enumerate(datas):
        for y,data in enumerate(sublist):
            picio=io.BytesIO(data)
            small_pic=pil.open(picio)
            outpic.paste(small_pic,(x*256,y*256))
    print('拼合完成！正在导出...')

    outpic.save(outfile)
    print('导出完成！')
    return frame


def getpic_s(x,y,z,source='google',outfile="out_single.png",style="s"):
    #获得单幅瓦片图像
    getpic(x,y,x,y,z,source,outfile,style)


if __name__ == '__main__':
    #下载西安 青龙寺地块 卫星地图
    mm=getpic(108.9797845,34.2356831,108.9949663,34.2275018,
        18,source='amap',style='m',outfile="myouta.png")

    printzb(mm)

