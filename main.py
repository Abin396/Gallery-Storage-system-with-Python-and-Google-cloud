from google.cloud import datastore, storage
from flask import Flask, render_template, request, redirect, url_for
from multiprocessing.sharedctypes import Value
import google.oauth2.id_token
import random, local_constants
from google.auth.transport import requests
import hashlib
from PIL import Image
from audioop import reverse
import datetime


app = Flask(__name__)
datastore_client = datastore.Client()
firebase_request_adapter = requests.Request()


def restoreUserInfo(claims):
 entity_key = datastore_client.key('UserInfo', claims['email'])
 entity = datastore_client.get(entity_key)
 return entity


def restoreUsers(Gallery):
    #make key objects out of all the keys and retrieve them
    user_id = Gallery['signer_list']
    user_keys = []
    for i in range(len(user_id)):
        user_keys.append(datastore_client.key('UserInfo', user_id[i]))
    User_list = datastore_client.get_multi(user_keys)
    return User_list




def restoreGallery(UserInfo):
    #make key objects out of all the keys and retrieve them
    Gallery_id = UserInfo['opengallery_list']
    gallery_keys = []
    for i in range(len(Gallery_id)):
        gallery_keys.append(datastore_client.key('Gallery', Gallery_id[i]))
    Gallery_list = datastore_client.get_multi(gallery_keys)
    return Gallery_list



def addGallery(claims, name):
    
    id = random.getrandbits(63)
    entity_key = datastore_client.key('Gallery', id)
    entity = datastore.Entity(key = entity_key)
    entity.update({
        'name': name,
        'Image_list': [],
        'signer_list': [],
        'initial_image': None
    })
    datastore_client.put(entity)
    addingUserToGallery(entity, claims['email'])
    return id



def addingUserToGallery(Gallery, email):
    user_keys = Gallery['signer_list']
    user_keys.append(email)
    Gallery.update({
        'signer_list': user_keys
    })
    datastore_client.put(Gallery)


def specificGallery(id):
    entity_key = datastore_client.key('Gallery', id)
    entity = datastore_client.get(entity_key)
    return entity


def dups(lstofelements):
    for elem in lstofelements:
        if lstofelements.count(elem) > 1:
            return True
    return False





def addingGalleryToUser(UserInfo, id):
    gallery_keys = UserInfo['opengallery_list']
    gallery_keys.append(id)
    UserInfo.update({
        'opengallery_list': gallery_keys
    })
    datastore_client.put(UserInfo)



def restoreImages(Gallery):
    Image_id = Gallery['Image_list']
    image_keys = []
    for i in range(len(Image_id)):
        image_keys.append(datastore_client.key('Image', Image_id[i]))
    Image_list = datastore_client.get_multi(image_keys)
    return Image_list

def addingImageToGallery(Gallery, id):
    image_keys = Gallery['Image_list']
    image_keys.append(id)
    Gallery.update({
        'Image_list': image_keys
    })
    datastore_client.put(Gallery)
    intialimage(Gallery)


def deleteGallery(Gallery_id, UserInfo):
    gallery_key = datastore_client.key('Gallery', Gallery_id)
    datastore_client.delete(gallery_key)

    Gallery_list = UserInfo['opengallery_list']
    Gallery_list.remove(Gallery_id)
    UserInfo.update({
        'opengallery_list' : Gallery_list
    })
    datastore_client.put(UserInfo)



def specificimage(id):
    entity_key = datastore_client.key('Image', id)
    entity = datastore_client.get(entity_key)
    return entity

def intialimage(Gallery):
    images = restoreImages(Gallery)
    images.sort(key=lambda x:x['timestamp'], reverse=True)
    if images:
        Gallery.update({
            'initial_image': images[0]['Image_url']
        })
        datastore_client.put(Gallery)


def deleteImage(Gallery_id, Image_id):
    Gallery = specificGallery(Gallery_id)
    image_list_keys = Gallery['Image_list']

    image_key = datastore_client.key('Image', Image_id)
    datastore_client.delete(image_key)
    image_list_keys.remove(Image_id)
    Gallery.update({
        'Image_list' : image_list_keys
    })
    datastore_client.put(Gallery)
    intialimage(Gallery)





@app.route('/shareuser/<int:id>', methods=['GET','POST'])
def share_user(id):
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user = None
    Gallery = None 
    ss_id = id
    if request.method == 'POST':
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
                user = restoreUserInfo(claims)
                Gallery = restoreGallery(user)
                entity_key = datastore_client.key('UserInfo', request.form['email'])
                entity = datastore_client.get(entity_key)
                if entity:

                    addingGalleryToUser(entity, ss_id)
            except ValueError as exc:
                error_message = str(exc)
        return redirect(url_for("openGallery", id=ss_id))
    else:
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
                Gallery = specificGallery(ss_id)
            except ValueError as exc:
                error_message = str(exc)
        return render_template('shareuser.html', Gallery=Gallery, ss_id=ss_id, user_data=claims, error_message=error_message)





@app.route('/delete_image/<int:id>', methods=['GET', 'POST'])
def delete_image(id):
    id_token = request.cookies.get("token")
    error_message = None
    ss_id = int(request.form['Gallery_id'])
    if request.method == 'POST':
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
                deleteImage( ss_id, id)
            except ValueError as exc:
                error_message = str(exc)
            return redirect(url_for("openGallery", id=ss_id))
    


@app.route('/openGallery/<int:id>', methods=['GET','POST'])
def openGallery(id):
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user = None
    Gallery = None
    ss_id = id
    users = None
    Images = None
    duplicate = False
    dupss = None
    if request.method == 'GET':
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
                user = restoreUserInfo(claims)
                Gallery = specificGallery(id)
                users = restoreUsers(Gallery)
                Images = restoreImages(Gallery)
                hash_list = []
                for Image in Images:
                    hash_list.append(Image['hash'])

                print((hash_list))
                print((set(hash_list)))
                dupss = len(hash_list) - len(set(hash_list))
                duplicate = dups(hash_list)
            except ValueError as exc:
                error_message = str(exc)
        return render_template('openGallery.html', user_data=claims, error_message=error_message, user=user,  Gallery= Gallery, ss_id=ss_id, users=users, Images=Images, duplicate=duplicate, dupss=dupss)





@app.route('/createimage/<int:id>', methods=['GET','POST'])
def create_image(id):
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user = None
    ss_id = id
    if request.method == 'POST':
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
                user = restoreUserInfo(claims)
                Gallery = specificGallery(ss_id)

                file = request.files['file_name']
                if file.filename.split(".")[1:] == ['jpg'] or file.filename.split(".")[1:] == ['JPG'] or file.filename.split(".")[1:] == ['jpeg'] or file.filename.split(".")[1:] == ['JPEG'] or file.filename.split(".")[1:] == ['png'] or file.filename.split(".")[1:] == ['PNG']:
                   storage_client = storage.Client(project=local_constants.PROJECT_NAME)
                   bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
                   blob = bucket.blob(file.filename)
                   blob.upload_from_string( file.read(), content_type=file.content_type)
                   blob.make_public()
                   url = blob.public_url
                else:
                    url = None
                hash = hashlib.md5(Image.open(file).tobytes()).hexdigest()
                randomKey = random.getrandbits(63)
                entity_key = datastore_client.key('Image', randomKey)
                entity = datastore.Entity(key = entity_key)
                entity.update({
                    'title' :    request.form['title'],
                    'Image_url' :  url,
                    'hash' : hash,
                    'timestamp' : datetime.datetime.now()
                })
                datastore_client.put(entity)
                id = randomKey
                addingImageToGallery(Gallery, id)
                intialimage(Gallery)
            except ValueError as exc:
                error_message = str(exc)
        return redirect(url_for("openGallery", id=ss_id))
    else:
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(
                        id_token, firebase_request_adapter)
                Gallery = specificGallery(ss_id)
                user = restoreUsers(Gallery)
            except ValueError as exc:
                error_message = str(exc)
        return render_template('createimage.html', Gallery=Gallery, ss_id=ss_id, user_data=claims, error_message=error_message,user=user)





@app.route('/edit_galleryname/<int:id>', methods=['GET','POST'])
def edit_galleryname(id):
    id_token = request.cookies.get("token")
    error_message = None
    ss_id = id
    claims=None
    if request.method == 'POST':
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
                user = restoreUserInfo(claims)
                Gallery = restoreGallery(user)
                exist = False
                for Gallery in Gallery:
                    if request.form['name'] == Gallery['name']:
                            exist = True
                            break
                if not exist:
                    Gallery = specificGallery(ss_id)
                    Gallery.update({
                        'name': request.form['name']
                    })
                    datastore_client.put(Gallery)
            except ValueError as exc:
              error_message = str(exc)
            return redirect(url_for("Gallist"))
    else:
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
                Gallery = specificGallery(ss_id)

            except ValueError as exc:
                error_message = str(exc)
        return render_template('editGallery.html', Gallery=Gallery, ss_id=ss_id,user_data=claims, error_message=error_message)



@app.route('/Gal_list', methods=["GET","POST"])
def Gallist():
   id_token = request.cookies.get("token")
   user_data=None
   error_message = None
   user = None
   Gallery = None
   dupss = None
   duplicate = None
   claims=None
   if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            user = restoreUserInfo(claims)
            if user == None:
                entity_key = datastore_client.key('UserInfo', claims['email'])
                entity = datastore.Entity(key = entity_key)
                entity.update({
                    'email': claims['email'],
                    'opengallery_list': []
                })
                datastore_client.put(entity)
                user = restoreUserInfo(claims)
            Gallery = restoreGallery(user)
            query = datastore_client.query(kind="Image")
            Images = list(query.fetch())
            hash_list = []
            for Image in Images:
                hash_list.append(Image['hash'])
            dupss = len(hash_list) - len(set(hash_list))
            duplicate = dups(hash_list)
        except ValueError as exc:
                error_message = str(exc)
        return render_template('Gal_list.html', error_message=error_message,user=user,Gallery=Gallery,dupss=dupss, duplicate=duplicate,user_data=claims)


@app.route('/delete_gallery/<int:id>', methods=['GET','POST'])
def delete_gallery(id):
    id_token = request.cookies.get("token")
    error_message=None
    claims=None
    Gallery_id = id
    Gallery=None
    if request.method == 'POST':

        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
                UserInfo = restoreUserInfo(claims)
                Gallery = specificGallery(Gallery_id)
                if not Gallery['Image_list']:
                    if len(Gallery['signer_list']) == 1:
                        deleteGallery(Gallery_id, UserInfo)
                else:
                    return redirect(url_for("Gallist", id=Gallery_id))
            except ValueError as exc:
                error_message = str(exc)
            return redirect('/Gal_list')
    else:
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
                Gallery = specificGallery(Gallery_id)
            except ValueError as exc:
                error_message = str(exc)
        return render_template("delte.html", Gallery_id=id, Gallery=Gallery, user_data=claims)










@app.route('/createGallery', methods=["GET","POST"])
def createGallery():
   id_token = request.cookies.get("token")
   user_data=None
   error_message = None
   UserInfo = None
   Gallery = None
   if request.method == "POST":
      if id_token:
         try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,firebase_request_adapter)
            UserInfo = restoreUserInfo(claims)
            Gallery = restoreGallery(UserInfo)
            exist = False
            for Gallery in Gallery:
                if request.form['name'] == Gallery['name']:
                        exist = True
                        break
            if not exist:
                id = addGallery(claims, request.form['name'])
                addingGalleryToUser(UserInfo, id)
         except ValueError as exc:
            error_message = str(exc)
      return redirect(url_for("Gallist"))
   else:
      if id_token:
         try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,firebase_request_adapter)
            UserInfo = restoreUserInfo(claims)
            Gallery =  restoreGallery(UserInfo)
         except ValueError as exc:
            error_message = str(exc)
      return render_template('createGallery.html', user_data=claims, error_message=error_message,UserInfo=UserInfo,Gallery=Gallery)


@app.route('/', methods=["GET","POST"])
def root():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user  = None
    Gallery = None
    count = None
    if request.method == "GET":
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(
                    id_token, firebase_request_adapter)
                user = restoreUserInfo(claims)
                if user == None:
                    entity_key = datastore_client.key('UserInfo', claims['email'])
                    entity = datastore.Entity(key = entity_key)
                    entity.update({
                        'email': claims['email'],
                        'opengallery_list': []
                    })
                    datastore_client.put(entity)
                    user  = restoreUserInfo(claims)
                Gallery =  restoreGallery(user )
            except ValueError as exc:
                error_message = str(exc)
        return render_template('home.html', user_data=claims, count=count, error_message=error_message, user =user , Gallery=Gallery)
    else :
        return render_template('index.html')


@app.route('/index', methods=["GET","POST"])
def mainpage():
   return render_template('index.html')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)