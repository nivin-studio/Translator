#!/usr/bin/python
#-*- encoding: utf-8 -*-

import sublime
import sublime_plugin
import threading
import urllib.request as request
import urllib.parse  as urlparse
import xml.dom.minidom as xmlparse

class Youdao(object):
    def __init__(self):
        self._translator_info = {
            'words'     : '', #关键字
            'trans'     : '', #译文
            'others'    : '', #其他译文
            'soundmark' : ''  #音标
        }

    def auto_translate(self, words):
        result = self.http_request(words)
        if not result:
            self._translator_info['words'] = '网络请求失败！'
            return self._translator_info

        trans     = self.parser_trans(result)
        others    = self.parser_others(result)
        soundmark = self.parser_soundmark(result)
        if not trans and not others and not soundmark:
            self._translator_info['words'] = '没有相关汉英互译结果!'
            return self._translator_info

        self._translator_info['words']     = words
        self._translator_info['trans']     = trans
        self._translator_info['others']    = others
        self._translator_info['soundmark'] = soundmark

        return self._translator_info

    def http_request(self, words):
        url    = 'http://dict.youdao.com/search'
        params = {
            'q'            : words,
            'keyfrom'      : 'deskdict.mini',
            'client'       : 'deskdict',
            'id'           : 'fef0101011fbaf8c',
            'vendor'       : 'unknown',
            'in'           : 'YoudaoDict',
            'appVer'       : '5.4.46.5554',
            'le'           : 'eng',
            'doctype'      : 'xml',
            'xmlVersion'   : 8.2,
            'appZengqiang' : 0,
            'LTH'          : 140
        }

        url = '%s?%s' % (url, urlparse.urlencode(params))
        req = request.Request(url)
        req.add_header('User-Agent','Youdao Desktop Dict (Windows 6.1.7601)')
       
        try:
            result = request.urlopen(req, timeout = 10).read()
            return xmlparse.parseString(result)
        except Exception as e:
            return ''

    def get_node_text(self, node, tag):
        nodes = node.getElementsByTagName(tag)
        if not nodes:
            return ''
        if not nodes[0].firstChild:
            return ''
        
        return nodes[0].firstChild.wholeText

    def parser_trans(self, node):
        result = []
        nodes  = node.getElementsByTagName('simple-dict')
        if not nodes:
            text = self.get_node_text(node, 'tran')
            if not text:
                return ''
            result.append(text)
            return result

        tr_nodes = nodes[0].getElementsByTagName('tr')
        if not tr_nodes:
            return ''

        for tr in tr_nodes:
            i_nodes = tr.getElementsByTagName('i')
            if i_nodes:
                text = ''.join([i.firstChild.wholeText for i in i_nodes if i.firstChild])
                result.append(text)

        return result

    def parser_others(self, node):
        nodes = node.getElementsByTagName('web-translation')
        if not nodes:
            return ''

        value_nodes = nodes[0].getElementsByTagName('value')
        if not value_nodes:
            return ''

        result = []
        for value in value_nodes:
            if value.firstChild:
                text = value.firstChild.wholeText
                result.append(text)

        return result

    def parser_soundmark(self, node):
        result  = []
        ukphone = self.get_node_text(node, 'ukphone')
        usphone = self.get_node_text(node, 'usphone')
        phone   = self.get_node_text(node, 'phone')

        if ukphone:
            result.append(' 英[%s] ' % ukphone)
        if usphone:
            result.append(' 美[%s] ' % usphone)
        if phone:
            result.append(' [%s] ' % phone)
        
        return result


class TranslateThread(threading.Thread):
    def __init__(self, words, view):
        self.view  = view
        self.words = words.replace('\n', '<br>')

        threading.Thread.__init__(self)

    def run(self):
        youdao = Youdao()
        result = youdao.auto_translate(self.words)
        
        self.show(result)

    def show(self, data):
        html = data['words']

        if data['soundmark']:
            html += ''.join(data['soundmark'])

        if data['trans']:
            html += '<br><br>' + '<br>'.join(['<a style=\"text-decoration:none;\" href=\"' + word + '\" >' + word + '</a>' for word in data['trans']])

        if data['others']:
            html += '<br><br>' + '<br>'.join(['<a style=\"text-decoration:none;\" href=\"' + word + '\" >' + word + '</a>' for word in data['others']])

        self.view.show_popup(html, sublime.COOPERATE_WITH_AUTO_COMPLETE, -1, 1000, 800, on_navigate=self.__replace_text)

    def __replace_text(self, text):
        self.view.run_command('insert', {'characters': text.replace('<br>', '\n')})
        self.view.hide_popup()

       
class TranslatorCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        region = self.view.sel()[0]
        if region.begin() != region.end():
            words  = self.view.substr(region)
            thread = TranslateThread(words, self.view)
            
            thread.run()