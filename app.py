from curses.textpad import rectangle
from distutils.log import debug
from email.mime import base
from fileinput import filename
from re import template
from tkinter.ttk import Style
from turtle import color, left
from flask import Flask, render_template, request, url_for, redirect
import requests
from PIL import Image, ImageDraw
from io import BytesIO
import os
import random
import time

UPLOAD_FOLDER = 'images'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Funcion para pintar cuadrado
def square(image_url, rectangle, origin):
    # Obtenemos la img enviada por el usuario
    response = requests.get(image_url)
    # La respuesta la parseamos a Bytes para que pueda interpretarlo Image
    img = Image.open(BytesIO(response.content))
    # Instanciamos el objeto Draw con la imagen
    dib = ImageDraw.Draw(img)
    # Lista de colores rgb para que pinte el cuadrado
    colors = [(0,255,255), (255,0,255), (0,255,0), (34,139,34), (255,69,0)]
    if origin == 'face':
        # Por cada coordenada que reciba pinto un cuadrado
        for cord in rectangle:
        # Para sacar el cuadrado de la cara es [left, top, left+width, top+height]
            dib.rectangle([cord['left'], cord['top'], cord['left']+cord['width'], cord['top']+cord['height']], width=5, outline=random.choice(colors))
    elif origin == 'image':
        # Por cada coordenada que reciba pinto un cuadrado
        for cord in rectangle:
        # Para sacar el cuadrado de la cara es [x, y, x+w, y+h]
            dib.rectangle([cord['x'], cord['y'], cord['x']+cord['w'], cord['y']+cord['h']], width=5, outline=random.choice(colors))
    img = img.save('./static/images/result.jpg')
    full_filename = 'result.jpg'

    return full_filename

@app.route("/")
def home():
    return render_template('home.html')

@app.route("/processCat", methods = ['POST'])
def cat_facts():
    base_url = 'https://catfact.ninja/fact'
    res = requests.get(base_url).json()
    fact = res['fact']
    image_url = request.form['url']

    return render_template('results.html', res=0)

@app.route("/face_recg", methods = ['POST'])
def face_recognition():
    base_url = 'https://practicafacerec.cognitiveservices.azure.com/'
    headers = {'Content-Type': 'application/json','Ocp-Apim-Subscription-Key': '0b7abf6aca944168892a9f19b05c37cd'}
    attributs_check = 'age,gender,smile,emotion,glasses'
    params = {'returnFaceId': 'true', 'returnFaceAttributes':attributs_check}
    image_url = request.form['url']
    body = {'url': image_url}
    service = 'face/v1.0/detect'
    service_type = 'face'

    response = requests.post(base_url+service, headers=headers, json=body, params=params).json()
    
    if 'error' in response:
        return render_template('results.html', msg=response['error']['message'], tipo='error')
    else:
        if len(response) > 0:
            rectangle = []
            face_id = []
            attributes = []
            emotions = []
            for resp in response:
                # Rectangulo mostrando la cara
                rectangle.append(resp['faceRectangle'])

                # FaceId
                face_id.append(resp['faceId'])

                # Atributos
                # copio el diccionario porque luego voy a eliminar un atributo el cual luego necesitaria.
                attr_aux = resp['faceAttributes'].copy()
                attr_aux.pop("emotion")
                attributes.append(attr_aux)

                # Emocion mas representativa
                emotions_aux = resp['faceAttributes']['emotion']
                max_val = max(emotions_aux, key=emotions_aux.get)
                emotions.append([max_val, emotions_aux[max_val]])

            image_rectangle = square(image_url, rectangle, service_type)

            return render_template('results.html', res=len(response),filename=image_rectangle, tipo=service_type, coord=rectangle, id=face_id, atr=attributes, emociones=emotions)

        else:
            return render_template('results.html', res=len(response), tipo=service_type)

@app.route("/image_recg", methods = ['POST'])
def image_recognition():
    base_url = 'https://practicacompvis.cognitiveservices.azure.com/'
    headers = {'Content-Type': 'application/json','Ocp-Apim-Subscription-Key': 'c37c2b3b36334b39927291ae24e0ed55'}
    attributs_check = 'description,color,tags,objects'
    params = {'visualFeatures': attributs_check, 'language': 'es'}
    image_url = request.form['url']
    body = {'url': image_url}
    service = 'vision/v3.2/analyze'
    service_type = 'image'

    response = requests.post(base_url+service, headers=headers, json=body, params=params).json()
    
    if 'error' in response:
        return render_template('results.html', msg=response['error']['innererror']['message'], tipo='error')
    else:
        if len(response) > 0:
            image_description = response['description']['captions'][0]['text']
            image_color = response['color']['accentColor']
            color_style = 'background-color: #' + image_color
            image_tags = [tag['name'] for tag in response['tags']]
            res = len(response['objects'])

            rectangle = [rect['rectangle'] for rect in response['objects']]

            image_rectangle = square(image_url, rectangle, service_type)
        
            return render_template('results.html', sty=color_style, filename=image_rectangle, descrp=image_description, col=image_color, tag=image_tags, len_tags= len(image_tags),tipo=service_type, res=res)
        else:
            return render_template('results.html', res=len(response), tipo=service_type)

@app.route("/text_recg", methods = ['POST'])
def text_recognition():
    base_url = 'https://practicaread.cognitiveservices.azure.com/'
    headers = {'Content-Type': 'application/json','Ocp-Apim-Subscription-Key': '8433b53b7cd44944b14233500b3126fe'}
    image_url = request.form['url']
    body = {'url': image_url}
    service = 'vision/v3.2/read/analyze'
    service_type = 'text'

    response = requests.post(base_url+service, headers=headers, json=body)
    url_response = response.__dict__['headers']['Operation-Location']
    check = 'false'

    while check != 'succeeded':
        result = requests.get(url_response, headers=headers).json()
        check = result['status']
        time.sleep(0.3)

    texto = [word['text'] for word in result['analyzeResult']['readResults'][0]['lines']]

    if 'error' in response:
        return render_template('results.html', msg=response['error']['message'], tipo='error')
    else:
        return render_template('results.html', tipo=service_type, text=texto)

@app.route("/display/<filename>")
def display_image(filename):
    return redirect(url_for('static', filename='images/' + filename), code=301)


if __name__ == '__main__':
    app.run(debug = True)