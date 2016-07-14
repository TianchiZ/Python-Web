import re, time, json, logging, hashlib, base64, asyncio, os

from coroweb import get, post
from aiohttp import web

from models import User, Vendor, DM, Firmware, next_id

from config import configs

from apis import Page, APIValueError, APIResourceNotFoundError,APIError
logging.basicConfig(level=logging.DEBUG)

#email的匹配正则表达式
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
#密码的匹配正则表达式
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

COOKIE_NAME = 'rawfirmware'
_COOKIE_KEY = configs.session.secret

#检测当前用户是不是admin用户
def check_admin(request):
	if request.__user__ is None or not request.__user__.admin:
		raise APIPermissionError()

#根据用户信息拼接一个cookie字符串
def user2cookie(user, max_age):
	# build cookie string by: id-expires-sha1
	#过期时间是当前时间+设置的有效时间
	expires = str(int(time.time() + max_age))
	#构建cookie存储的信息字符串
	s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
	L = [user.id , expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
	#用-隔开，返回
	return '-'.join(L)

#根据cookie字符串，解析出用户信息相关的
@asyncio.coroutine
def cookie2user(cookie_str):
	#cookie_str是空则返回
	if not cookie_str:
		return None
	try:
		#通过'-'分割字符串
		L = cookie_str.split('-')
		#如果不是3个元素的话，与我们当初构造sha1字符串时不符，返回None
		if len(L) != 3:
			return None
		#分别获取到用户id，过期时间和sha1字符串
		uid, expires, sha1 = L
		#如果超时，返回None
		if int(expires) < time.time():
			return None
		#根据用户id查找库，对比有没有该用户
		user = yield from User.find(uid)
		#没有该用户返回None
		if user is None:
			return None
		#根据查到的user的数据构造一个校验sha1字符串
		s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
		#比较cookie里的sha1和校验sha1，一样的话，说明当前请求的用户是合法的
		if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
			logging.info('invalid sha1')
			return None
		user.passwd = '******'
		#返回合法的user
		return user
	except Exception as e:
		logging.excepetion(e)
		return None

@get('/show_all_users')
def show_all_users():
	users = yield from User.findAll()
	logging.info('to index...')

	return {
		'__template__':'test.html',
		'users': users
	}

@get('/api/users')
def api_get_users(request):
	users = yield from User.findAll(orderBy='created_at desc')
	logging.info('users = %s and type = %s' % (users, type(users)))
#	for u in users:
#		u.passwd = '******'
	return dict(users=users)

#注册页面
@get('/register')
def register():
	return {
		'__template__': 'register.html'
	}

#登陆页面
@get('/signin')
def signin():
	return {
		'__template__':'signin.html'
	}

#登出操作
@get('/signout')
def signout(request):
	referer = request.headers.get('Referer')
	r = web.HTTPFound(referer or '/')
	#清理掉cookie得用户信息数据
	r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
	logging.info('user signed out')
	return r

#注册请求
@post('/api/users')
def api_register_user(*, email, name, passwd):
	#判断name是否存在，且是否只是'\n', '\r',  '\t',  ' '，这种特殊字符
	if not name or not name.strip():
		raise APIValueError('name')
	#判断email是否存在，且是否符合规定的正则表达式
	if not email or not _RE_EMAIL.match(email):
		raise APIValueError('email')
	#判断passwd是否存在，且是否符合规定的正则表达式
	if not passwd or not _RE_SHA1.match(passwd):
		raise APIValueError('passwd')

	#查一下库里是否有相同的email地址，如果有的话提示用户email已经被注册过
	users = yield from User.findAll('email=?', [email])
	if len(users) > 0:
		raise APIError('register:failed', 'email', 'Email is already in use.')

	#生成一个当前要注册用户的唯一uid
	uid = next_id()
	#构建shal_passwd
	sha1_passwd = '%s:%s' % (uid, passwd)

	admin = False
	if email == 'admin@163.com':
		admin = True

	#创建一个用户（密码是通过sha1加密保存）
	user = User(id = uid, name = name.strip(), email=email, passwd = hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image = 'http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest(), admin=admin)

	#保存这个用户到数据库用户表
	yield from user.save()
	logging.info('save user OK')
	#构建返回信息
	r = web.Response()
	#添加cookie
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age = 86400, httponly = True)
	#只把要返回的实例的密码改成'******'，库里的密码依然是正确的，以保证真实的密码不会因返回而暴漏
	user.passwd = '******'
	#返回的是json数据，所以设置content-type为json的
	r.content_type= 'application/json'
	#把对象转换成json格式返回
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

#登陆请求
@post('/api/authenticate')
def authenticate(*, email, passwd):
	#如果email或passwd为空，都说明有错误
	if not email:
		raise APIValueError('email', 'Invalid email')
	if not passwd:
		raise APIValueError('passwd', 'Invalid  passwd')
	#根据email在库里查找匹配的用户
	users = yield from User.findAll('email=?', [email])
	#没找到用户，返回用户不存在
	if len(users) == 0:
		raise APIValueError('email', 'email not exist')
	#取第一个查到用户，理论上就一个
	user = users[0]
	#按存储密码的方式获取出请求传入的密码字段的sha1值
	sha1 = hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))
	#和库里的密码字段的值作比较，一样的话认证成功，不一样的话，认证失败
	if user.passwd != sha1.hexdigest():
		raise APIValueError('passwd', 'Invalid passwd')
	#构建返回信息
	r = web.Response()
	#添加cookie
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	#只把要返回的实例的密码改成'******'，库里的密码依然是正确的，以保证真实的密码不会因返回而暴漏
	user.passwd = '******'
	#返回的是json数据，所以设置content-type为json的
	r.content_type = 'application/json'
	#把对象转换成json格式返回
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

@get('/')
def index():
	return {
		'__template__': 'index.html',
	}

@get('/manage/upload')
def upload():
	return {
		'__template__': 'upload.html',
	}

@get('/api/drive')
def api_drive():
	vendors = yield from Vendor.findAll(orderBy='vendor_name')
	models = yield from DM.findAll(orderBy='model_name')
	firmwares = yield from Firmware.findAll()
	return dict(vendor=vendors,model=models,firmware=firmwares)

@post('/manage/upload/files')
def manage_upload_files(request):
	data = yield from request.post()
	vendor = data['vd_id']
	model = data['md_id']
	fw_rev = data['fw_rev']
	selection = data['adde_file']
	file_type = data['fw_type']
	linkspeed = data['fw_linkspeed']
	driveformat = data['fw_driveformat']
	fw_count = yield from Firmware.findAll(where='fw_vendor_name=? and fw_model_name=? and firmware_revision=? and fw_type=? and fw_drive_linkspeed=? and fw_drive_format=?', args=[vendor, model, fw_rev, file_type, linkspeed, driveformat])

	#Add both files
	if selection == 'Add Both Files':
		try:
			fwfile_name = data['fw_file'].filename
			fwfile = data['fw_file'].file
			clfile_name = data['cl_file'].filename
			clfile = data['cl_file'].file
			releasedate = data['fw_releasedate']
		except AttributeError as e:
			return web.StreamResponse(status=889)

		if len(fw_count) > 0:
			return web.StreamResponse(status=888)

		else:
			fw_dir = os.path.join(os.path.abspath('.'), 'firmwares', vendor, model)
			if not os.path.exists(fw_dir):
				os.makedirs(fw_dir)
			fw_path = os.path.join(fw_dir, fwfile_name)
			with open(fw_path, "wb") as f:
				buf = fwfile.read()
				f.write(buf)
				logging.info("File {} succeeded uploaded".format(fwfile_name))
			cl_path = os.path.join(fw_dir, clfile_name)
			with open(cl_path, "wb") as f:
				buf = clfile.read()
				f.write(buf)
				logging.info("File {} succeeded uploaded".format(clfile_name))
			firmware = Firmware(user_id=request.__user__.id, user_email=request.__user__.email,user_name=request.__user__.name,user_image=request.__user__.image,fw_vendor_name=vendor,fw_model_name=model,fw_type=file_type,fw_drive_format=driveformat,fw_drive_linkspeed=linkspeed,firmware_revision=fw_rev,firmware_name=fwfile_name,changelist_name=clfile_name,changelist_status='Download',fw_release_date=releasedate)
			yield from firmware.save()
			return 'Success'

	#Add firmware file only
	elif selection == 'Add Firmware Only':
		try:
			fwfile_name = data['fw_file'].filename
			fwfile = data['fw_file'].file
			releasedate = data['fw_releasedate']
		except AttributeError as e:
			return web.StreamResponse(status=889)

		if len(fw_count) > 0:
			return web.StreamResponse(status=888)

		else:
			fw_dir = os.path.join(os.path.abspath('.'), 'firmwares', vendor, model)
			if not os.path.exists(fw_dir):
				os.makedirs(fw_dir)
			fw_path = os.path.join(fw_dir, fwfile_name)
			with open(fw_path, "wb") as f:
				buf = fwfile.read()
				f.write(buf)
				logging.info("File {} succeeded uploaded".format(fwfile_name))
			clfile_name = 'NA'
			firmware = Firmware(user_id=request.__user__.id, user_email=request.__user__.email,user_name=request.__user__.name,user_image=request.__user__.image,fw_vendor_name=vendor,fw_model_name=model,fw_type=file_type,fw_drive_format=driveformat,fw_drive_linkspeed=linkspeed,firmware_revision=fw_rev,firmware_name=fwfile_name,changelist_name=clfile_name,changelist_status='NA',fw_release_date=releasedate)
			yield from firmware.save()
			return 'Success'

	#Add changelist only
	elif selection =='Add Changelist Only':
		try:
			clfile_name = data['cl_file'].filename
			clfile = data['cl_file'].file
		except AttributeError as e:
			return web.StreamResponse(status=889)

		if len(fw_count) == 0:
			return web.StreamResponse(status=887)

		else:
			fw_dir = os.path.join(os.path.abspath('.'), 'firmwares', vendor, model)
			cl_path = os.path.join(fw_dir, clfile_name)
			with open(cl_path, "wb") as f:
				buf = clfile.read()
				f.write(buf)
				logging.info("File {} succeeded uploaded".format(clfile_name))
			fw_update = Firmware(firmware_id=fw_count[0].firmware_id, user_id=fw_count[0].user_id, user_email=fw_count[0].user_email,user_name=fw_count[0].user_name,user_image=fw_count[0].user_image,fw_vendor_name=fw_count[0].fw_vendor_name,fw_model_name=fw_count[0].fw_model_name,fw_type=fw_count[0].fw_type,fw_drive_format=fw_count[0].fw_drive_format,fw_drive_linkspeed=fw_count[0].fw_drive_linkspeed,firmware_revision=fw_count[0].firmware_revision,firmware_name=fw_count[0].firmware_name, changelist_name=clfile_name,changelist_status='Download',fw_release_date=fw_count[0].fw_release_date,created_at=time.time())
			yield from fw_update.update()
			return 'Success'

	#Delete the files
	elif selection == 'Delete Entry':
		if len(fw_count) == 0:
			return web.StreamResponse(status=887)
		else:
			fw_del = os.path.join(os.path.abspath('.'), 'firmwares', vendor, model, fw_count[0].firmware_name)
			if fw_count[0].changelist_name == 'NA':
				os.remove(fw_del)
			else:
				cl_del = os.path.join(os.path.abspath('.'), 'firmwares', vendor, model, fw_count[0].changelist_name)
				os.remove(fw_del)
				os.remove(cl_del)
			firmware_del = yield from Firmware.find(fw_count[0].firmware_id)
			yield from firmware_del.remove()
			return 'Success'



@post('/manage/upload/addmodel')
def manage_upload_addmodel(request):
	data = yield from request.post()
	vendor = data['vd_add']
	model = data['md_add']
	select = data['adde']
	vendor_db = yield from Vendor.findAll('vendor_name = ?', vendor)
	vid = vendor_db[0]['vendor_id']
	md_count = yield from DM.findAll(where='vendor_id=? and model_name=?', args=[vid,model])

	# Add model
	if select=='1':
		if len(md_count)==1:
			return web.StreamResponse(status=999)
		else:
			model_new = DM(vendor_id=vid,model_name=model)
			yield from model_new.save()
			return 'Success'

	#Delete model
	else:
		if len(md_count)==0:
			return web.StreamResponse(status=997)
		else:
			fw_count = yield from Firmware.findAll(where='fw_vendor_name=? and fw_model_name=?',args=[vendor,model])
			if len(fw_count)>0:
				return web.StreamResponse(status=998)
			else:
				model_del = yield from DM.find(md_count[0].model_id)
				yield from model_del.remove()
				return 'Success'