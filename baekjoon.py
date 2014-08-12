#!/usr/bin/python3
import sublime, sublime_plugin
import re
import urllib.parse as urp
import http.client as hcl
import time
import threading
import json

langlist=[
"C", "C++", "Pascal", "Java", "Ruby 1.8", "Bash", "Python", "PHP", "Perl", "C# 2.0",
"Objective-C", None, "Go", "Fortran", "Scheme", "Scala", "Lua", "node.js", None, "Ada",
"VB.NET 2.0", "awk", "OCaml", "Brainfuck", "Whitespace", "Groovy", "Tcl", "Assembly", "Python3", "D",
None, None, "PyPy", "Clojure", "Rhino", None, None, "F#", "SpiderMonkey", None,
None, "Pike", "Perl6", "sed", "Rust", None, "Boo", "Intercal", "bc", "C++11",
None, None, "Prolog", "Nemerle", "Cobra", "Nimrod", None, None, "Text", "C (Clang)",
"C++ (Clang)", "Io", "C# 4.0", None, "Objective-C++", "Ruby 1.9"
]
class BaekjoonSubmitCommand(sublime_plugin.TextCommand):
	settings=sublime.load_settings('Baekjoon.sublime-settings')
	lglist=[]
	def run(self, edit): self.bungi()
	def bungi(self):
		localv=self.view.settings()
		publicv=self.settings
		if localv.get('bjn_ft')==None: sublime.set_timeout(self.inputft, 50)
		elif publicv.get('id', '')=='': sublime.set_timeout(self.inputid, 50)
		elif localv.get('bjn_pw', '')=='':
			if localv.get('bjn_id', '')=='': localv.set('bjn_id', publicv.get('id'))
			if publicv.get('password', '')=='': sublime.set_timeout(self.inputpw, 50)
			else:
				localv.set('bjn_pw', publicv.get('password'))
				if localv.get('bjn_qn')==None: self.findqn()
				else: self.publish()
		elif localv.get('bjn_qn')==None: self.findqn()
		else: self.publish()

	def inputid(self): self.view.window().show_input_panel("id: ", "", self.ondoneid, on_change=None, on_cancel=None)
	def inputpw(self): self.view.window().show_input_panel("password: ", "", self.ondonepw, on_change=None, on_cancel=None)
	def inputqn(self): self.view.window().show_input_panel("question number: ", "", self.ondoneqn, on_change=None, on_cancel=None)
	def inputft(self):
		a=self.settings.get('default_lang')
		self.lglist=langlist[:]
		while None in self.lglist:self.lglist.remove(None)
		if a!=None:
			self.lglist.remove(langlist[a])
			self.lglist=[langlist[a]]+self.lglist[:]
		self.view.window().show_quick_panel(self.lglist, self.ondoneft, selected_index=0)
		#TODO: Get syntax highlight and assume language
	def ondoneid(self, value):
		self.settings.set('id', value)
		sublime.save_settings('Baekjoon.sublime-settings')
		self.bungi()
	def ondonepw(self, value):
		self.view.settings().set('bjn_pw', value)
		self.bungi()
	def ondoneqn(self, value):
		self.view.settings().set('bjn_qn', int(value))
		self.publish()
	def ondoneft(self, value):
		self.view.settings().set('bjn_ft', langlist.index(self.lglist[value]))
		self.bungi()
	def findqn(self):
		v=re.compile('.*[\\\\/](\d+?)(?:\.(\w+))?$')
		a=v.match(self.view.file_name()) if self.view.file_name()!=None else None
		if a:
			b=a.groups()
			self.view.settings().set('bjn_qn', int(b[0]))
			self.bungi()
			#TODO assume programming language by file extension
		else: sublime.set_timeout(self.inputqn, 50)
	def publish(self):
		l=self.view.settings()
		p=urp.urlencode({'username': l.get('bjn_id'), 'password': l.get('bjn_pw'),
			'problem_id': l.get('bjn_qn'), 'language': l.get('bjn_ft'), 'version': '1.1',
			'source': self.view.substr(sublime.Region(0, self.view.size()))})
		conn=hcl.HTTPSConnection('www.acmicpc.net', 443)
		conn.request('POST', '/cmd/submit', p, {'Content-type': 'application/x-www-form-urlencoded'})
		r=conn.getresponse().read()
		conn.close()
		BaekjoonResultApiCall(r).start()

class BaekjoonSetLangCommand(sublime_plugin.TextCommand):
	settings=sublime.load_settings('Baekjoon.sublime-settings')
	lglist=langlist[:]
	while None in lglist:lglist.remove(None)
	def run(self, edit):
		self.view.window().show_quick_panel(
			self.lglist, self.ondone,
			selected_index=0
		)
	def ondone(self, value):
		self.settings.set('default_lang', langlist.index(self.lglist[value]))
		sublime.save_settings('Baekjoon.sublime-settings')

class BaekjoonResultApiCall(threading.Thread):
	def __init__(self, o):
		self.o=json.loads(o.decode('utf-8'))
		del self.o['error']
		threading.Thread.__init__(self)
	def run(self):
		rs=[u'기다리는 중', u'재채점을 기다리는 중', u'컴파일 하는 중', u'채점 중', None,
			u'출력 형식이 잘못되었습니다', u'틀렸습니다', u'시간 초과', u'메모리 초과', u'출력 초과',
			u'런타임 에러', u'컴파일 에러']
		for i in range(1, 60):
			conn=hcl.HTTPConnection('www.acmicpc.net', 80)
			conn.request('POST', '/cmd/status', urp.urlencode(self.o), {'Content-type': 'application/x-www-form-urlencoded'})
			ru=conn.getresponse().read()
			r=json.loads(ru.decode('utf-8'))
			conn.close()
			if r['error']:
				sublime.status_message(r['error_text'])
				return
			a=r['result']
			e=int(a['result'])
			if e==3:
				if 'progress' in r: sublime.status_message(u'%s (%s%%)' % (rs[e], r['progress']))
				else: sublime.status_message(u'%s' % rs[e])
			elif e<3: sublime.status_message(rs[e])
			elif e==4:
				sublime.status_message(u'맞았습니다!! / 메모리: %(memory)sKB, 시간: %(time)sms, 코드 길이: %(code_length)sB' % a)
				break
			elif e<10:
				sublime.status_message(u'%s / 코드 길이: %s' % (rs[e], a['code_length']))
				break
			else:
				sublime.status_message(u'%s / 메시지: %s' % (rs[e], r['error_text']))
				break
			time.sleep(1)