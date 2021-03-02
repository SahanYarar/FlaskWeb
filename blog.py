from flask import Flask,render_template,flash,redirect,url_for,session,logging,request,g
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.handlers.sha2_crypt import sha256_crypt
from functools import wraps
import MySQLdb   
from werkzeug.utils import secure_filename
import os

#Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim:",validators=[validators.Length(min=4,max=25,message="İsim en az 4 en fazla 25 karaktar olması gerekmektedir....")])
    username = StringField("Kullanıcı Adı:",validators=[validators.Length(min=5,max=25,message="Kullanıcı adı en az 5 en fazla 25 karakter olması gerekmektedir....")])
    email = StringField("Email Adresi:",validators=[validators.Email(message="Lütfen geçerli bir e-mail adersi giriniz.........")])
    password = PasswordField("Parola:",validators=[
        validators.DataRequired(message="Lütfen bir paralo belirleyin"),
        validators.EqualTo(fieldname="confirm",message="Parolanız Uyuşmuyor")      
    ])
    confirm=PasswordField("Parola Doğrula")
class LoginForm(Form):
    username=StringField("Kullanıcı Adı:")
    password=PasswordField("Parola:")

UPLOAD_FOLDER = '/path/to/the/uploads'
ALLOWED_EXTENSIONS = {"jpg", "jpeg"}

app = Flask(__name__)
app.secret_key="ybblog"
app.config["MYSQL_HOST"]="localhost"
app.config["MYSQL_USER"]="root"
app.config["MYSQL_PASSWORD"]=""
app.config["MYSQL_DB"]="ybblog"
app.config["MYSQL_CURSORCLASS"]="DictCursor"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mysql=MySQL(app)


@app.route("/")
def index():
    
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/login",methods=["GET","POST"])
def login():
    form=LoginForm(request.form)
    if request.method=="POST":
        username=form.username.data
        password_entered=form.password.data

        cursor=mysql.connect.cursor()
        sorgu="Select * From users where username = %s"#Herşeyi alıyor datadan
        result=cursor.execute(sorgu,(username,))#Yanlışsa sonuç 0 geliyor
        if result >0:
            data=cursor.fetchone()
            real_password=data["password"]
            if sha256_crypt.verify(password_entered,real_password):#Verify doğrula
                flash("Başarıyla giriş yaptınız","success")
                session["logged_in"]=True
                session["username"]=username

                return redirect(url_for("index"))
            else:
                flash("Parolanızı kontrol ediniz.","danger")
                return redirect(url_for("login"))    
            
        else:
            flash("Böyle bir kullanıcı adı bulunmamaktadır.","danger")
            return redirect(url_for("login"))
            
    return render_template("login.html",form=form)
#Kullanıcı Giriş Decorator'ı
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)

        else:
            flash("Giriş Yapmanız Gerekmektedir!!","danger")
            return redirect(url_for("login"))
    return decorated_function


#Register Kayıt olma
@app.route("/register",methods = ["GET","POST"])
def register():
    
    form =RegisterForm(request.form)

    if request.method =="POST" and form.validate():
        name=form.name.data
        username=form.username.data
        email=form.email.data
        password=sha256_crypt.encrypt(form.password.data)

        cursor=mysql.connection.cursor()
        sorgu="Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"

        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarıyla kayıt oldunuz....","success")

        return redirect(url_for("login"))

    else:
        return render_template("register.html",form=form)
        
#Logout
@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Çıkış gerçekleştirildi..","success")
    return redirect(url_for("index"))

#Makale Sayfası
@app.route("/articles")
def articles():
    cursor=mysql.connection.cursor()
    sorgu="Select * From articles"

    result=cursor.execute(sorgu)
    if result > 0:
        articles=cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:
        return render_template("articles.html")
        

@app.route("/dashboard")
@login_required
def dashboard():
    cursor=mysql.connection.cursor()
    sorgu="Select * From articles where author= %s"

    result=cursor.execute(sorgu,(session["username"],))
    if result > 0:
        articles=cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    
    else:
        return render_template("dashboard.html")



#Makale ekleme
@app.route("/addarticle",methods=["GET","POST"])
@login_required
def addarticle():
    form=ArticleForm(request.form)
    if request.method=="POST" and form.validate():
        title=form.title.data
        content=form.content.data
        cursor=mysql.connection.cursor()
        sorgu="Insert into articles(title,author,content)VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale Başarıyla Eklendi","success")
        return redirect(url_for("dashboard"))

    return render_template("addarticle.html",form=form)
#Makale form
class ArticleForm(Form):
    title =StringField("Makale Başlığı",validators=[validators.length(min=5,max=100)])
    content=TextAreaField("Makale İçeriği",validators=[validators.length(min=10)])

#Makale Silme
@app.route("/delete/<string:Id>")
@login_required
def delete(Id):
    cursor=mysql.connection.cursor()
    sorgu="Select * from articles where author=%s and Id=%s"
    result=cursor.execute(sorgu,(session["username"],Id))

    if result > 0:
        sorgu2="Delete from articles where Id = %s"
        cursor.execute(sorgu2,(Id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya bu işleme yetkiniz yok...","danger")
        return redirect(url_for("index"))

#Makale Güncelleme
@app.route("/edit/<string:Id>",methods=["GET","POST"])
@login_required
def update(Id):
    if request.method=="GET":
        cursor=mysql.connection.cursor()
        sorgu="Select * from articles where Id=%s and author=%s"
        result=cursor.execute(sorgu,(Id,session["username"]))
        if result == 0:
            flash("Böyle bir makale bulunmamakta veya yetkiniz yok","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form=ArticleForm()

            form.title.data=article["title"]
            form.content.data=article["content"]
            return render_template("update.html",form=form)
             
    else:#Post request
        form=ArticleForm(request.form)
        newTitle=form.title.data
        newContent=form.content.data
        sorgu2="Update articles Set title =%s,content=%s where Id=%s"
        cursor=mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,Id))
        mysql.connection.commit()
        flash("Makale Başarıyla Güncellendi","success")
        return redirect(url_for("dashboard"))



#Detay Sayfası
@app.route("/article/<string:Id>")
def article(Id):
    cursor=mysql.connection.cursor()
    sorgu="Select * from articles where Id =%s"
    result=cursor.execute(sorgu,(Id,))
    if result > 0:
        article=cursor.fetchone()
        return render_template("article.html",article=article)
        
    else:
        return render_template("article.html")
        
#Arama URL
@app.route("/search",methods=["GET","POST"])
def search():
    if request.method=="GET":
        flash("Lütfen arama butonunu kullanınız...","danger")
        return redirect(url_for("index"))
    else:
        keyword=request.form.get("keyword")
        cursor = mysql.connection.cursor()
        sorgu="Select * from articles where title like '%"+ keyword +"%' "  
        result=cursor.execute(sorgu) 
        if result ==0:
            flash("Aranan kelimeye uygun makale bulunamadı...","warning")
            return redirect(url_for("articles"))
        else:
            articles=cursor.fetchall()
            return render_template("articles.html",articles=articles)


           
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
            
@app.route("/profile",methods=["GET","POST"])
@login_required
def profile():
    if request.method == "POST":
        # check if the post request has the file part
        if 'file' not in request.files:
            flash("Dosya bulunamadı")
            return redirect(request.url("profile"))
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == " ":
            flash("Lütfen resim seçiniz","danger")
            return redirect(request.url("profile"))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for("profile",filename=filename))
    else:
        cursor=mysql.connection.cursor()
        sorgu="Select * from users "
        result=cursor.execute(sorgu)
        if result >0:
            profil=cursor.fetchone()
            return render_template("profile.html",profil=profil)  
              
                                    
            

if __name__ =="__main__":
    app.run(debug=True)












