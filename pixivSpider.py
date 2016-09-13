import os, json, urllib, urllib2, cookielib, threading, Queue
from bs4 import BeautifulSoup
from datetime import datetime
from PIL import Image

class PixivSpider:
    def __init__(self, username, password):
        self.imgs = []
        self.__html = "http://www.pixiv.net/ranking.php?mode=monthly&content=illust"
        self.__originalLink = "http://www.pixiv.net/member_illust.php?mode=medium&illust_id="
        self.__opener = None
        self.q = Queue.Queue()
        self.username = username
        self.password = password

    def CreateDir(self, path = "img/"):
        if not os.path.exists(path): os.makedirs(path)

    def __MakeJsonUrl(self, page):
        return self.__html + "&p=" + str(page) + "&format=json"

    def __GetJsonData(self, html):
        data = json.loads(urllib.urlopen(html).read())
        if data is None:
            return None
        else:
            for info in data["contents"]:
                img = {}
                img["id"] = info["illust_id"]
                img["rank"] = info["rank"]
                self.imgs.append(img)
                #print img["id"], '\t', img["rank"]
    def __loginRequest(self):
        cookie = cookielib.MozillaCookieJar("cookie.txt")
        self.__opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
        header = {
            "Accept-Language": "zh-CN,zh;q=0.8",
            'Referer': 'https://www.pixiv.net/login.php?return_to=0',
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36"
        }
        loginInfo = urllib.urlencode({
            'mode': 'login',
            'pass': self.password,
            'pixiv_id': self.username,
        })
        loginUrl = "https://www.pixiv.net/login.php"
        request = urllib2.Request(loginUrl, data=loginInfo, headers=header)
        self.__opener.open(request)
        cookie.save(ignore_discard = True, ignore_expires = True)

    def __DownloadRequest(self, refererUrl, originalUrl):
        header = {
            "Accept-Language": "zh-CN,zh;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36"
        }
        header['referer'] = refererUrl
        request = urllib2.Request(originalUrl, headers=header)
        return self.__opener.open(request).read()

    class MyThread(threading.Thread):
        def __init__(self, filename, referer, src, opener, q, idx, total):
            threading.Thread.__init__(self)
            self.filename = filename
            self.referer = referer
            self.src = src
            self.opener = opener
            self.q = q
            self.total = total
            self.idx = idx

        def run(self):
            header = {
                "Accept-Language": "zh-CN,zh;q=0.8",
                "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36"
            }
            header['referer'] = self.referer
            request = urllib2.Request(self.src, headers=header)
            data = self.opener.open(request).read()
            file = open(self.filename, "wb")
            file.write(data)
            file.close()
            self.q.put(self.idx)
            print "Finished: ", self.idx, "/", self.total

    def GetImages(self):
        self.CreateDir()
        for i in range(1, 7, 1):
            self.__GetJsonData(self.__MakeJsonUrl(i))
        self.__loginRequest()
        total = len(self.imgs)
        t1 = datetime.now()
        print t1
        count = 1
        for img in self.imgs:
            id = img["id"]
            referer = self.__originalLink + str(id)
            data = self.__opener.open(referer).read()
            soup = BeautifulSoup(data, "lxml")
            tags = soup.find_all("img", attrs={"class": "original-image"})
            if len(tags) > 0:
                src = tags[0].attrs['data-src']
                #print "#" + str(img["rank"]), src
                # file = open(self.__fatherPath + "#" + str(img["rank"]).zfill(3) + src[-4 : len(src)], 'wb')
                # file.write(self.__DownloadRequest(referer, src))
                # file.close()
                mt = self.MyThread("img/" + "#" + str(img["rank"]).zfill(3) + src[-4 : len(src)], referer, src, self.__opener, self.q, count, total)
                mt.start()
            else:
                data = self.__opener.open(self.__originalLink.replace("medium", "manga", 1) + str(id)).read()
                soup = BeautifulSoup(data, "lxml")
                tags = soup.find_all("img", attrs={"data-filter": "manga-image"})
                for tag in tags:
                    idx = "_" + str(int(tag.attrs['data-index']) + 1)
                    src = tag.attrs['data-src']
                    #print "#" + str(img["rank"]) + idx, src
                    # file = open(self.__fatherPath + "#" + str(img["rank"]).zfill(3) + idx + src[-4 : len(src)], 'wb')
                    # file.write(self.__DownloadRequest(referer, src))
                    # file.close()
                    mt = self.MyThread("img/" + "#" + str(img["rank"]).zfill(3) + idx + src[-4 : len(src)], referer,
                                       src, self.__opener, self.q, count, total)
                    mt.start()
            count += 1
        t2 = datetime.now()
        check = self.q.get()
        #while check < total:
        #    check = max(check, self.q.get())

        print t2, '\t', (t2.hour * 3600 + t2.second + t2.minute * 60) - (t1.second + t1.minute * 60 + t1.hour * 3600), 'second(s) passed'

    def MakeHtml(self):
        htmlFile = open("img/" + "!.html", "wb")
        htmlFile.writelines("<html>\r\n<head>\r\n<title>Pixiv</title>\r\n</head>\r\n<body>\r\n")
        htmlFile.writelines("<script>window.onload = function(){"
                            "var imgs = document.getElementsByTagName('img');"
                            "for(var i = 0; i < imgs.length; i++){"
                            "imgs[i].onclick = function(){"
                            "if(this.width == this.attributes['oriWidth'].value && this.height == this.attributes['oriHeight'].value){"
                            "this.width = this.attributes['oriWidth'].value * 1.0 / this.attributes['oriHeight'].value * 200;"
                            "this.height = 200;"
                            "}else{this.width = this.attributes['oriWidth'].value ;"
                            "this.height = this.attributes['oriHeight'].value;}}}};</script>")
        for i in os.listdir("img/"):
            if i[-4:len(i)] in [".png", ".jpg", ".bmp"]:
                filename = i
                imgSize = Image.open("img/" + filename).size
                width, height = imgSize
                filename = filename.replace("#", "%23")
                #htmlFile.writelines("<a href = \"%s\">"%("./" + filename))
                htmlFile.writelines("<img src = \"%s\" width = \"%dpx\" height = \"%dpx\" oriWidth = %d oriHeight = %d />\r\n"
                                    %("./" + filename, width * 1.0 / height * 200, 200, width, height))
                #htmlFile.writelines("</a>\r\n")
        htmlFile.writelines("</body>\r\n</html>")
        htmlFile.close()
#########################################################################
pSpider = PixivSpider(raw_input("your username:"), raw_input("your password:"))
pSpider.GetImages()
pSpider.MakeHtml()