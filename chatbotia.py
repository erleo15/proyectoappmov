import logging
import operator
import telegram
import time
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters 
from bs4 import BeautifulSoup
import urllib3
import pyaudio
import wave
import json
from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import os
import requests
from bs4 import BeautifulSoup
from gtts import gTTS 
import pyrebase
import conversion
from datetime import datetime,date,timedelta
from firebase import firebase


mensajeglobal = ""
class Proyecto:

	def __init__(self):
		##Control de fechas
		_hoy = date.today()
		_dias = timedelta(days=2555)
		#########
		
		#####Configuracion para conectar al bot######
		self.updater = Updater(token='API_KEY_TELEGRAM_BOT',use_context=True)
		self.dispatcher = self.updater.dispatcher
		#####ComandHandler para llenar los datos 
		self.handler_start = CommandHandler('llenardatos',self.iniciarLlenar)
		self.dispatcher.add_handler(self.handler_start) 
		#####ComandHandler para responder encuesta
		self.handler_responder = CommandHandler('responderencuesta',self.responder_encuesta)
		self.dispatcher.add_handler(self.handler_responder)
		self.responder_handler = MessageHandler(Filters.text, self.responder_encuesta)
		self.dispatcher1 = self.updater.dispatcher
		self.dispatcher1.add_handler(self.responder_handler)
		#
		##handler para ingresar los datos por texto
		self.echo_handler = MessageHandler(Filters.text, self.pedir_datos)
		self.dispatcher.add_handler(self.echo_handler)
		##termina handler para ingresar datos por texto 
		
		#Message handler para hacer pedir datos por voz 
		self.reconocer = MessageHandler(Filters.voice, self.pedir_datos_voz)
		self.dispatcher.add_handler(self.reconocer)
 
		
		####################

		#####log para ver errores sucede en el programa
		logging.basicConfig(format='%(asctime)s - %(name)s %(levelname)s - %(message)s ',level=logging.INFO);
		
		
		
		##Variables para gestionar los datos que se ingresen####
		"""self.nombreguardar = "Hernan Leonel";
		self.fechaguardar = "01/02/2018";
		self.nivelguardar = "1";
		self.centroguardar = "centro educativo las girnaldas";
		self.edadcalculada = 170;
		self.pk_generado = "";
		self.rango_fecha = "";"""
		self.nombreguardar = "";
		self.fechaguardar = "";
		self.nivelguardar = ""; 
		self.edadcalculada = -1;
		self.pk_generado = "";
		self.rango_fecha = "";
		self.fecha_rango_inferior = (_hoy -_dias) 
		self.anio_menor = self.fecha_rango_inferior.year; 
		self.datos_nino = {};
		self.tabla_nino = "Nino"
		self.tabla_pregunta = "Pregunta"
		self.tabla_terapeuta = "Terapeuta"
		self.tabla_respuesta = "Respuesta"
		self.cedula_terapeuta = ""
		self.is_pedir_datos = True;
		self.is_encuesta = False;
		self.is_ultimo = True
							# A  B  C  D 	
		self.listaPuntajes = [0, 0, 0, 0];
		self.diagnostico = [
			'Retraso de lenguaje secundario a déficit auditivo',
			'Retraso de lenguaje secundario a trastorno del espectro autista',
			'Dislalia',
			'Disfluencia (3 – 5 años)  ejercicos \nTrastorno del desarrollo de la fluidez del habla (partir de los 5 años ) ',
			'Disfluencia',
			'ejercicos Trastorno del desarrollo de la fluidez del habla ']
		self.numero_pregunta = 1; 
		#############################
		####Referente a la base de datos####
		
		config =  {
		    "apiKey": '',
		    "authDomain": "",
		    "databaseURL": "",
		    "projectId": "",
		    "storageBucket": "",
		    "messagingSenderId": "",
		    "appId": ""
			}; #Se obtiene directamente desde la consola de administracion de firebase
		
		
		self.fb_firebase = firebase.FirebaseApplication('URL_BD_FIREBASE', None)
		
		fb_pyrebase = pyrebase.initialize_app(config)
		self.fb_pyrebase = fb_pyrebase.database()##declarando la base de datos
		######termina referente a la base de datos
		self.updater.start_polling() 
		self.updater.idle() 
		

	def iniciarLlenar(self,update, context): 
		self.is_ultimo = True
		self.is_pedir_datos = True;
		if("logout" == update.message.text):
			self.cedula_terapeuta = ""; 
			self.fechaguardar = "";
			self.nivelguardar = -1;
			self.nombreguardar = "";
			return "";
			
		if(len(self.cedula_terapeuta) <1):
			context.bot.send_message(chat_id = update.message.chat_id, text = "Primero escriba login:cedula:contraseña estoy en iniciarllenar")
			
			self.login(update = update, context = context)
			return ""
		context.bot.send_message(chat_id=update.effective_chat.id,text = "Ingrese el nombre (nombre apellido)");

 	 

########Inicia Pedir Datos########
	def pedir_datos(self,update,context):
		if("logout" == update.message.text):
			self.cedula_terapeuta = "";
			return "";
		if(len(self.cedula_terapeuta) <1):
			context.bot.send_message(chat_id = update.message.chat_id, text = "Primero escriba login:cedula:contraseña estoy en pedir_datos")
			self.login(update = update, context = context)
			return ""
		self.nombre =update.message.text

		
		 

		#PAra detectar el nombre
		if(" " in self.nombre):
			self.nombreguardar = self.nombre;
			context.bot.send_message(chat_id=update.effective_chat.id,text = "Ingrese Fecha de Nacimiento (dia/mes/año)");
		#Para detectar la fecha
		if("/" in self.nombre):
			self.fechaguardar = self.nombre;
			context.bot.send_message(chat_id=update.effective_chat.id,text = "Ingrese Nivel (numero)");
		valor = 0; 
		try:
			valor = int(self.nombre)
			self.nivelguardar = self.nombre
			print("valores: "+self.nombreguardar+";"+self.fechaguardar)
			self.calcular_edad(fecha = self.fechaguardar);
			self.guardarNino(update = update, context = context);
			

		except ValueError:
			print ("ATENCIÓN: Debe ingresar un número entero.")
     	

########Termina Recepcion de datos########


######Metodo responder encuesta

	def responder_encuesta(self,update,context):
		_is_cumple = str(update.message.text).strip()
		if("logout" == _is_cumple):
			self.cedula_terapeuta = "";
			return "";
		
		if(len(self.cedula_terapeuta) <1):
			context.bot.send_message(chat_id = update.message.chat_id, text = "Primero escriba login:cedula:contraseña estoy en responder_encuesta")
			self.login(update = update, context = context)
			return ""

		
		if(self.is_pedir_datos):
			self.pedir_datos(update=update,context=context)
			return ""

		try:
			int(self.datos_nino)
			context.bot.send_message(chat_id = update.message.chat_id, text = "No se tiene datos del nino. Siga las siguientes instrucciones: \n1) Escriba /llenardatos \n "+
			"2)Llene los datos correspondientes al nino") 
			return "";
		except :
			print("Si hay datos")
			
		print("llego a responder encuesta");
		##va a llegar en formato r=si o r = no
		print("mensaje recibido: "+ _is_cumple)
		if(self.edadcalculada<=2555):
			edad = 2555;
			if(self.edadcalculada<=2190):
				edad = 2190
				if(self.edadcalculada<=1825):
					edad = 1825
					if(self.edadcalculada<=1460):
						edad = 1460
						if(self.edadcalculada<=1095):
							edad = 1095
							if(self.edadcalculada<=730):
								edad = 730
								if(self.edadcalculada<=330):
									edad = 330
									if(self.edadcalculada<=180 and self.edadcalculada>=0):
										edad = 180
		print("edad en dias: "+str(self.edadcalculada))
		print("edad perteneciente: "+str(edad))
	
		
		
		_enunciado_actual = self.fb_firebase.get("/"+self.tabla_pregunta+"/"+str(edad)+"/"+str(self.numero_pregunta),"enunciado")
		_lista_codigo_actual = self.fb_firebase.get("/"+self.tabla_pregunta+"/"+str(edad)+"/"+str(self.numero_pregunta),"codigo") 
		
		

		print(str(_enunciado_actual)+":"+str(_lista_codigo_actual));
		sig_enunciado = self.fb_firebase.get("/"+self.tabla_pregunta+"/"+str(edad)+"/"+str(self.numero_pregunta+1),"enunciado")

		generatedAudio = "audio.wav"
        
		try:
			with open(generatedAudio, 'rb') as file:
				text = sig_enunciado
			file = gTTS(text=text, lang = 'ES')
			file.save(generatedAudio)
		except :
			print("ya llego al ultimo")
		 

		if(sig_enunciado is None): 
			context.bot.send_message(chat_id = update.message.chat_id,text = "Encuesta Terminada")	
			context.bot.send_message(chat_id = update.message.chat_id,text = 
			"Puntajes: \nA:"+str(self.listaPuntajes[0])+"\nB: "+str(self.listaPuntajes[1])+
			"\nC: "+str(self.listaPuntajes[2])+"\nD: "+str(self.listaPuntajes[3]))
			 

			resultado = {
				"A":self.listaPuntajes[0],
				"B":self.listaPuntajes[1],
				"C":self.listaPuntajes[2],
				"D":self.listaPuntajes[3]
           		}

			print(resultado)
			dic_diagnostico = sorted(resultado.items(), key=operator.itemgetter(1), reverse=True)
			codigo_mayor = ""
			for i in enumerate(dic_diagnostico):
				print(i[1][0], 'has spend', resultado[i[1][0]])
				codigo_mayor = str(i[1][0])
				break

			print(codigo_mayor)
			_diagnostico = ""
			if(codigo_mayor == "A"):
				_diagnostico = self.diagnostico[0]
			if(codigo_mayor == "B"):
				_diagnostico = self.diagnostico[1]
			if(codigo_mayor == "C"):
				_diagnostico = self.diagnostico[2]
			if(codigo_mayor == "D"):
				_diagnostico = self.diagnostico[3]
			context.bot.send_message(chat_id = update.message.chat_id,text = _diagnostico)
			context.send_audio(chat_id = update.message.chat_id, audio = open(generatedAudio,'rb'))

			self.is_ultimo = False
			self.is_pedir_datos = True
			self.is_encuesta = False
		

		if(_is_cumple == "si" and self.is_ultimo): 
			context.bot.send_message(chat_id = update.message.chat_id,text = str(self.numero_pregunta+1)+") "+str(sig_enunciado))
			context.bot.send_voice(chat_id = update.message.chat_id, voice = open(generatedAudio,'rb'))
			self.numero_pregunta = self.numero_pregunta +1;

		if(_is_cumple == "no" and self.is_ultimo): 
			context.bot.send_message(chat_id = update.message.chat_id,text = str(self.numero_pregunta+1)+") "+str(sig_enunciado))
			context.bot.send_voice(chat_id = update.message.chat_id, voice = open(generatedAudio,'rb'))
			self.numero_pregunta = self.numero_pregunta +1;
			for i in _lista_codigo_actual: 
				_codigo = str(i)
				_puntaje = self.fb_firebase.get("/"+self.tabla_pregunta+"/"+str(edad)+"/"+str(self.numero_pregunta)+"/porcentaje",_codigo)
				print("puntaje de "+_codigo+": "+str(_puntaje));
				if(str(i) == "A"):
					self.listaPuntajes[0] = self.listaPuntajes[0]+int(str(_puntaje))
				if(str(i) == "B"):
					self.listaPuntajes[1] = self.listaPuntajes[1]+int(str(_puntaje))
				if(str(i) == "C"):
					self.listaPuntajes[2] = self.listaPuntajes[2]+int(str(_puntaje))
				if(str(i) == "D"):
					self.listaPuntajes[3] = self.listaPuntajes[3]+int(str(_puntaje))

		if(_is_cumple != "no" and _is_cumple != "si" and self.is_ultimo):
			context.bot.send_message(chat_id = update.message.chat_id,text = "Debe responde con: si o no'")
			with open(generatedAudio, 'rb') as file:
				text = str(_enunciado_actual)
			file = gTTS(text=text, lang = 'ES')
			file.save(generatedAudio) 
			
			context.bot.send_message(chat_id = update.message.chat_id,text = str(self.numero_pregunta)+") "+str(_enunciado_actual))
			context.bot.send_voice(chat_id = update.message.chat_id, voice = open(generatedAudio,'rb'))
			return ""
		


		print(_is_cumple)
		
		
		
		 
		
		datos = {
			"Nino" : 
				{
					self.pk_generado :
						{
							"nombre" : self.nombreguardar,
							"fecha" : self.fechaguardar,
							"nivel" : self.nivelguardar, 
							"terapeuta": self.correo_terapeuta
						}	
				},
			"Pregunta" : 
				{
					edad : 
						{
							self.numero_pregunta : 
								{ 
									"enunciado": _enunciado_actual ##construir enunciado
								}
						}
					
				},
			"terapeuta" : 
				{
					self.correo_terapeuta :
						{
							"nombre": self.nombre_terapeuta #construir nombre terapeuta
						}
				},
			"cumple" : _is_cumple##construir valor
			}

		self.fb_pyrebase.child(self.tabla_respuesta).push(datos)
		
		#Genero muestro los datos con una bandera..hay q pensar :)


######metodo guardarNino

	def guardarNino(self,update,context):
		if("logout" == update.message.text):
			self.cedula_terapeuta = "";
			return ""; 
		if(len(self.cedula_terapeuta) <1):
			context.bot.send_message(char_id = update.message.chat_id, text = "Primero escriba login:cedula:contraseña")
			self.login(update = update, context = context)
			return ""
		if(self.edadcalculada<0):
			context.bot.send_message(chat_id=update.effective_chat.id,text = "La fecha ingresada no es valida.\nA continuacion repita la fecha\n"
			+"Recuerde que debe de ser menor a la fecha actual");
			return ""  

		datos = {
			"nombre" : self.nombreguardar,
			"fecha" : self.fechaguardar,
			"nivel" : self.nivelguardar, 
			"terapeuta" : self.cedula_terapeuta 
		}
		self.datos_nino = datos;  
		print(datos) 
		results = self.fb_pyrebase.child(self.tabla_nino).push(datos)
		self.pk_generado = str(results).split("'")[3]; 
		print(results); 
		context.bot.send_message(chat_id=update.effective_chat.id,text = "Se guardo el nino");
		self.is_pedir_datos = False;
		##self.dispatcher.remove_handler(handler = self.echo_handler)
   ##Conectar al ibmwatson
	def conectar(self, apikey= 'API_KEY_IBM-WATSON', _url='_URL_IBMWATSON_SERVICE'):
        
		authenticator = IAMAuthenticator(apikey)
		self.servicio_stt = SpeechToTextV1(authenticator=authenticator) 
		return True

 
	#####Metodo para pasar de letras a numero
	def letras_to_numero(self,inicio,fin,numero_en_letras):
		numero_en_letras = numero_en_letras.replace(" ","")
		if("primero" in numero_en_letras):
			numero_en_letras = "uno";

		for i in range(inicio, (fin+1), 1):
			#numero = str(conversion.numero_to_letras(i)).replace("  "," ");
			numero = str(conversion.numero_to_letras(i)).replace(" ","");
			print("numero a letra: "+numero);
			if(numero == numero_en_letras):
				return i;
		return -1

	def mes_to_numero(self,mes_en_letras):
		_meses = ['enero', 'febrero', 'marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
		j = 1;
		for i in _meses:
			if(i==mes_en_letras):
				return j;
			j = j+1;
		return -1;

	#####Metodo para pedir datos del niño por voz
	def pedir_datos_voz(self, update, context):
		if(len(self.cedula_terapeuta) <1):
			context.bot.send_message(char_id = update.message.chat_id, text = "Primero escriba login:cedula:contraseña")
			self.login(update = update, context = context)
			return ""
		file = context.bot.getFile(update.message.voice.file_id)
		file.download('./audio.wav')    
		self.conectar()  
		with open("audio.wav", 'rb') as _audio:
			res= json.dumps(self.servicio_stt.recognize(audio= _audio, content_type='audio/ogg', timestamps=True, model='es-ES_NarrowbandModel', word_confidence = True).get_result(), indent=2)
			cadena = str(res) 
			data = json.loads(cadena)
			busqueda = ''
			for client in data['results']:
				for j in client['alternatives']:
					print(j['transcript'])
					self.nombre=str(j['transcript']).strip();


		if ("guardar" in self.nombre.strip()):
			self.guardarNino(update = update, context = context);
			return ""	
 
		 

		if(" de " in self.nombre):
			_fecha_en_letras = (self.nombre+"").strip();
			_fecha_split = _fecha_en_letras.split("de")
			_dia1 = _fecha_split[0].strip()
			_mes1 = _fecha_split[1].strip()
			_anio1 = _fecha_split[2].strip()
			print("atento: "+_fecha_split[0]);
			_dia = self.letras_to_numero(numero_en_letras = _dia1,inicio = 1, fin = 32 ) 
			_mes = self.mes_to_numero(mes_en_letras = _mes1)
			_mes = str(_mes).replace(" ","");

			_anio = self.letras_to_numero(numero_en_letras = _anio1, inicio= self.anio_menor, fin =date.today().year)
			 

			_dia = _dia if (int(_dia)>=10) else "0"+str(_dia)
			_mes = _mes if (int(_mes)>=10) else "0"+str(_mes)
			self.fechaguardar = str(_dia)+"/"+str(_mes)+"/"+str(_anio)
			
			try:
				self.calcular_edad(fecha = self.fechaguardar)
			except :
				print ("ATENCIÓN: Debe ingresar un número entero.")
				context.bot.send_message(chat_id = update.effective_chat.id, text = 
				"Fecha fuera del rango:\nSe debe de ingresar la fecha desde: \n"+str(self.fecha_rango_inferior)+
				" hasta hoy: "+str(date.today()));
				
				return "";

			print("esta fecha a guardar: "+self.fechaguardar)
			context.bot.send_message(chat_id=update.effective_chat.id,text = 
			"DATOS A GUARDAR \nNombre: "+self.nombreguardar+"\nFechaNacimiento: "+self.fechaguardar
			+"\nNivel: "+self.nivelguardar+
			"\nIngrese Nivel o diga guardar");
			return "";
		
		if(" " in self.nombre):
			self.nombreguardar = self.nombre;
			context.bot.send_message(chat_id=update.effective_chat.id,text = 
			"DATOS A GUARDAR \nNombre: "+self.nombreguardar+"\nFechaNacimiento: "+self.fechaguardar
			+"\nNivel: "+self.nivelguardar+
			"\nIngrese fecha de Nacimiento (dia de mes de año) o diga guardar");
			return ""
		

		valor = 0;

		
		try:
			numero_en_letras = str(self.nombre).strip();
			valor = self.letras_to_numero(numero_en_letras = numero_en_letras, inicio = 0, fin = 5)
			#valor = int(self.nombre)
			self.nivelguardar = str(valor)
			print("valores: "+self.nombreguardar+";"+self.fechaguardar)
			context.bot.send_message(chat_id=update.effective_chat.id,text = 
			"DATOS A GUARDAR \nNombre: "+self.nombreguardar+"\nFechaNacimiento: "+self.fechaguardar
			+"\nNivel: "+self.nivelguardar+"\nDiga guardar");
			return ""
			#self.guardarNino(update = update, context = context);


		except ValueError:
			print ("ATENCIÓN: Debe ingresar un número entero.")
		
		if ("guardar" in self.nombre):
			self.guardarNino(update = update, context = context);
			return ""
	#####Termina metodo para pedir datos del niño por voz

#####Metodos para calcular la edad dado un fecha 
	def dias_entre(self,d1, d2):
		return abs(d2 - d1).days;

	def calcular_edad(self, fecha):
		_fecha = str(fecha).split("/");
		_d1 = date(int(_fecha[2]),int(_fecha[1]),int(_fecha[0]))
		_d2 = date.today()
		print(str(_d1)+":dos fechas:"+str(_d2))
		self.edadcalculada = self.dias_entre(d1 = _d1 , d2 = _d2) 
		if((self.edadcalculada > 2555)):
			self.edadcalculada = -1;
		print(self.dias_entre(d1 = _d1 , d2 = _d2))
	###finaliza metodos para calcular la edad

	######Metodo para hacer login
	def login(self,update,context): 
		if("login:" not in update.message.text):
			print("login mijin :( ")
			return False;
		print ("si es para login" )
		try:
			cedula = str(update.message.text).split(":")[1];
			contrasenia = str(update.message.text).split(":")[2];
			print(cedula+" llegada de cedula")
		except:
			context.bot.send_message(chat_id=update.effective_chat.id,text = "El formato par login no es correcto");
			return False

		result = str(self.fb_firebase.get(self.tabla_terapeuta,cedula));#fb_firebase.get(self.tabla_terapeuta,cedula);
		print(result)
		try:
			_pass = result.split("'")[11];
			_nombre = result.split("'")[7];
		except:
			context.bot.send_message(chat_id=update.effective_chat.id,text = "No existe el usuario con cedula: "+cedula);
			return False;
		if(contrasenia == _pass):
			context.bot.send_message(chat_id=update.effective_chat.id,text = "Bienvenido "+_nombre+"\nPara cerrar sesion escriba logout");
			self.cedula_terapeuta = cedula
			self.correo_terapeuta = cedula
			self.nombre_terapeuta = _nombre
			return True
		print(_pass);
		context.bot.send_message(chat_id=update.effective_chat.id,text = "Credenciales incorrectas");
		return False;
    ######

if __name__ == '__main__':
	oscarito = Proyecto()
	