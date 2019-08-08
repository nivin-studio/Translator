#!/usr/bin/python
#-*- encoding: utf-8 -*-


import sublime
import sublime_plugin
import threading
import urllib.request as request
import urllib.parse  as urlparse
from xml.dom.minidom import parseString


class TrsInfo(object):
    word      = ""
    trans     = ""
    web_trans = ""
    phonetic  = ""


class Youdao(object):

    def __init__(self):
        self._trs_info = TrsInfo()

    def _init_trs(self):
        self._trs_info.word      = ""
        self._trs_info.trans     = "没有找到相关的汉英互译结果。"
        self._trs_info.web_trans = ""
        self._trs_info.phonetic  = ""

    def auto_translate(self, words):
        self._init_trs()
        self._trs_info.word = words
        url  = "http://dict.youdao.com/search"
        data = {"keyfrom" : "deskdict.mini", "q" : words, "doctype" : "xml", "xmlVersion" : 8.2,
        "client" : "deskdict", "id" : "fef0101011fbaf8c", "vendor": "unknown", 
        "in" : "YoudaoDict", "appVer" : "5.4.46.5554", "appZengqiang" : 0, "le" : "eng", "LTH" : 140}

        url = "%s?%s" % (url, urlparse.urlencode(data));
        req = request.Request(url)
        req.add_header('User-Agent','Youdao Desktop Dict (Windows 6.1.7601)')
        sublime.status_message(url)
        try:
            ret = request.urlopen(req, timeout=10).read()
        except Exception as e:
            sublime.status_message(e)
            return self._trs_info
        
        dom = parseString(ret)

        self._trs_info.trans     = self.parser_trans(dom)
        self._trs_info.web_trans = self.parser_web_trans(dom)
        self._trs_info.phonetic  = self.parse_phonetic(dom)
        return self._trs_info

    def parser_trans(self, node):
        nodes = node.getElementsByTagName("simple-dict")
        if not nodes:
            return ""

        tr_nodes = nodes[0].getElementsByTagName("tr")
        if not tr_nodes:
            return ""

        strs = ""
        for tr in tr_nodes:
            i_nodes = tr.getElementsByTagName("i")
            if i_nodes:
                word = ''.join([i.firstChild.wholeText for i in i_nodes if i.firstChild])
                word = "<a style=\"text-decoration:none;\" href=\""+word+"\" >"+word+"</a>" + "<br>";
                strs += word

        return strs

    def parser_web_trans(self, node):
        nodes = node.getElementsByTagName("web-translation")
        if not nodes:
            return ""  

        value_nodes = nodes[0].getElementsByTagName("value")
        if not value_nodes:
            return ""

        strs = ""
        for value in value_nodes:
            if value.firstChild:
                word = "<a style=\"text-decoration:none;\" href=\""+value.firstChild.wholeText+"\" >"+value.firstChild.wholeText+"</a>" + "<br>";
                strs += word

        return strs

    def get_node_text(self, node, tag):
        nodes = node.getElementsByTagName(tag)
        if not nodes:
            return ""
        if not nodes[0].firstChild:
            return ""
        return nodes[0].firstChild.wholeText

    def parse_phonetic(self, node):
        phonetics = ""
        ukphone = self.get_node_text(node, "ukphone")
        if ukphone: phonetics  += "英[%s] " % ukphone
        usphone = self.get_node_text(node, "usphone")
        if usphone: phonetics += "美[%s]" % usphone
        phone = self.get_node_text(node, "phone")
        if phone: phonetics += "[%s]" % phone
        return phonetics

        
class TranslatorCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        region = self.view.sel()[0]
        if region.begin() != region.end():
            word = self.view.substr(region)
            thread = translate_comment(word, self.view)
            thread.run(edit)
        else:
            sublime.status_message('must be a word')


youdao = Youdao()
class translate_comment(threading.Thread):
    def __init__(self, word, view):
        self.word = word
        self.view = view
        threading.Thread.__init__(self)

    def run(self, edit):
        trs_info = youdao.auto_translate(self.word)

        html = """<span class="keyword">{t.word}</span> <span class="string quoted">{t.phonetic}</span><br><br><span class="string quoted">{t.trans}</span><br><span class="string quoted">{t.web_trans}</span>""".format(t=trs_info)
        self.view.show_popup(html, sublime.COOPERATE_WITH_AUTO_COMPLETE, -1, 600, 500, on_navigate=self.changeWord)

    def changeWord(self, word):
        sels = self.view.sel()[0]
        self.view.run_command("insert", {"characters": word})
       