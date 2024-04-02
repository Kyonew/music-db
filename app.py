# Importation des modules nécessaires
from flask import Flask, render_template, request
import sqlite3
from fuzzywuzzy import fuzz, process
import api_key
import requests

app = Flask(__name__, template_folder="templates") # on cherche les fichiers HTML dans le dossier template, afin de les afficher ultérieurement


@app.route("/") # On défini la fin de l'url (ici "/" donc par défaut) à la fonction qui se situe juste en dessous ("home")
def home():
    """Cette fonction permet d'afficher la page d'accueil de l'application"""
    
    connexion = sqlite3.connect('Music_db.db') # Connexion à la base de données
    
    curseur = connexion.cursor() # Création du "curseur" qui permettra de faire des requêtes à la base de données

    curseur.execute("""SELECT COUNT(*) FROM ALBUMS""") # On récupère le nombre d'albums présents dans la bdd (base de données)
    albumsSize = curseur.fetchone()[0] # Ici on ne veut récupérer que la première valeur qui est renvoyée. Curseur.fetchone() renvoie : (nombre,). Donc le [0] est nécessaire pour ne sortir que le nombre présent

    curseur.execute("""SELECT COUNT(*) FROM ARTISTE""") # Le nombre d'artistes présents dans la bdd
    artisteSize = curseur.fetchone()[0] 

    curseur.execute("""SELECT ALBUMS.Nom, GenreName, Pseudo, ALBUMS.idAlbum, cover_url
                        FROM ALBUMS 
                        JOIN GENRE ON ALBUMS.idGenre = GENRE.idGenre
                        JOIN ARTISTE ON ALBUMS.idArtiste = ARTISTE.idArtistes
                        WHERE ALBUMS.isLiked = 'true'
                        """) # Ici, on récupère le nom de l'album, son genre, le pseudo de l'artiste, l'id de l'album ainsi que sa couverture des albums "likés" (ajoutés aux favoris)
    
    albumsLike = curseur.fetchall() # .fetchall() permet de récupérer toutes les informations sous forme de liste.
    curseur.execute("""SELECT ARTISTE.idArtistes, Pseudo, pic_url
                    FROM ARTISTE
                    WHERE ARTISTE.isLiked = 'true'
                    """) # Récupération des id des artistes likés, de leur pseudo ainsi que leur photo de profil
    
    artisteLike = curseur.fetchall()
    return render_template("home.html", albumsSize=albumsSize, artisteSize=artisteSize, albumsLike=albumsLike, artisteLike=artisteLike) # Ce return permet d'afficher la page HTML de "home" (l'accueil)
                                                                                                                                        # Les arguments passés font références à des variables qui sont utilisés dans l'HTML de Home.

@app.route("/addAlbum")
def addAlbum():
    """Cette fonction permet d'afficher la page d'ajout d'album"""
    return render_template("addAlbum.html")


@app.route('/albums')
def albums():
    """
    Cette fonction permet d'afficher tous les albums présents dans la bdd avec leurs
    informations comme : leur id, Nom, Date de sortie, Nombre de morceaux, Genre, et le pseudo de l'artiste
    
    """
    
    connexion = sqlite3.connect('Music_db.db')
    curseur = connexion.cursor()
    
    # Requête SQL pour récupérer les albums
    curseur.execute("""SELECT idAlbum, ALBUMS.Nom, DateSortie, NbrMorceaux, GenreName, Pseudo, ALBUMS.isLiked
                            FROM ALBUMS
                            JOIN GENRE ON ALBUMS.idGenre = GENRE.idGenre
                            JOIN ARTISTE ON ALBUMS.idArtiste = ARTISTE.idArtistes""")

    
    # Récupérer les résultats de la requête
    elements = curseur.fetchall()
    
    # Fermer la connexion à la base de données
    connexion.close()

    return render_template("albums.html", elements=elements)


@app.route('/likeAlbum')
def likeAlbum():
    """
    Cette fonction permet de "liker" un album, c'est à dire l'ajouter aux favoris
    
    """
    
    connexion = sqlite3.connect('Music_db.db')
    curseur = connexion.cursor()
    albumID = request.args.get('albumID') # On récupère l'argument "albumID" de l'url. exemple: /album?albumID=104
                                          # La valeur albumID sera égale à 104

    
    # Requête SQL pour mettre à jour l'album
    curseur.execute("""UPDATE ALBUMS  
                       SET isLiked = 'true'
                       WHERE idAlbum = (?)""", (albumID,))
    
    connexion.commit() # On envoie
    curseur.execute("""SELECT idAlbum, ALBUMS.Nom, DateSortie, NbrMorceaux, GenreName, ARTISTE.Pseudo, ALBUMS.isLiked, cover_url
                            FROM ALBUMS
                            JOIN GENRE ON ALBUMS.idGenre = GENRE.idGenre
                            JOIN ARTISTE ON ALBUMS.idArtiste = ARTISTE.idArtistes
                            WHERE ALBUMS.idAlbum = (?)""", (albumID,)) # On réaffiche les éléments avec les informations à jour

    elements = curseur.fetchall()
    
    connexion.close()

    return render_template('album.html', elements=elements, albumID=albumID)


@app.route('/notLikeAlbum')
def notLikeAlbum():
    """
    Cette fonction permet de supprimer son "like" d'album, c'est à dire l'enlever des favoris
    
    """
    connexion = sqlite3.connect('Music_db.db')
    curseur = connexion.cursor()
    albumID = request.args.get('albumID')

    # Requête SQL pour sélectionner les éléments
    curseur.execute("""UPDATE ALBUMS  
                       SET isLiked = 'False' 
                       WHERE idAlbum = (?)""", (albumID,))
    
    connexion.commit()
    
    curseur.execute("""SELECT idAlbum, ALBUMS.Nom, DateSortie, NbrMorceaux, GenreName, ARTISTE.Pseudo, ALBUMS.isLiked, cover_url
                            FROM ALBUMS
                            JOIN GENRE ON ALBUMS.idGenre = GENRE.idGenre
                            JOIN ARTISTE ON ALBUMS.idArtiste = ARTISTE.idArtistes
                            WHERE ALBUMS.idAlbum = (?)""", (albumID,))

    elements = curseur.fetchall()

    connexion.close()
    
    return render_template('album.html', elements=elements, albumID=albumID)


@app.route('/artistes')
def artistes():
    """
    Cette fonction permet d'afficher tous les artistes présents dans la bdd avec leurs
    informations telles que leur id, Pseudo, Nom, Prénom, Genre
    """
    
    connexion = sqlite3.connect('Music_db.db')
    curseur = connexion.cursor()
    
    
    curseur.execute("""SELECT ARTISTE.idArtistes, Pseudo, ARTISTE.Nom, Prenom, GenreName, ARTISTE.isLiked
                        FROM ARTISTE
                        JOIN GENRE ON ARTISTE.Genre = GENRE.idGenre""")

    elements = curseur.fetchall()
    
    connexion.close()
    
    return render_template("artistes.html", elements=elements)


@app.route('/search', methods=['POST', 'GET'])
def search():
    """
    Cette fonction gère la barre de recherche de l'application
    
    """
    
    elements = '' # On défini elemnts sur rien pour pouvoir afficher des résultats en conséquences, si il n'y a aucun résultat par exemple
    vide = None
    if request.method == 'POST': # on vérifie que l'utilisateur envoie bien des informations (sa recherche)
        try:
            query = request.form['query'] # query correspond à ce que l'utilisateur à tapé dans la barre de recherche (type : str)
            
            with sqlite3.connect('Music_db.db') as connexion: # on admet connexion à sqlite3.connect(...), exactement comme avant

                curseur = connexion.cursor()
                
                curseur.execute("""SELECT idAlbum, ALBUMS.Nom, DateSortie, NbrMorceaux, GenreName, Pseudo
                                   FROM ALBUMS
                                   JOIN GENRE ON ALBUMS.idGenre = GENRE.idGenre
                                   JOIN ARTISTE ON ALBUMS.idArtiste = ARTISTE.idArtistes
                                   WHERE ALBUMS.Nom = :query OR DateSortie = :query OR GenreName = :query OR Pseudo = :query""", {"query": query})
                
                elements = curseur.fetchall()
                
                if elements == []:
                    vide = True  # s'il n'y aucun résultat, alors vide existe
                
                connexion.close()
        except: # Si cela n'a pas fonctionné, on clôt l'accès à la bdd
            connexion.close()
        finally:    
            return render_template('search.html', query=query, elements=elements, vide=vide) # on affiche les recherches et on passe en arguments, les éléments et la présence de vide
                

@app.route('/artiste')
def artiste():
    """
    Cette fonction permet d'afficher les données sur un artiste en particulier, en fonction de son ID.
    Données récupérées : Pseudo, Nom, Prénom, Genre, Date de naissance, s'il est liké, sa photo de profil
    
    """
    
    artisteID = request.args.get('artisteID') # on récupère son ID dans l'url
    connexion = sqlite3.connect('Music_db.db')
    curseur = connexion.cursor()

    curseur.execute("""SELECT Pseudo, Nom, Prenom, GenreName, Daybirth, ARTISTE.isLiked, pic_url
                        FROM ARTISTE
                        JOIN GENRE ON ARTISTE.Genre = GENRE.idGenre
                        WHERE ARTISTE.idArtistes = (?)""", (artisteID,))


    elements = curseur.fetchall()
    
    
    return render_template('artiste.html', elements=elements, artisteID=artisteID)


@app.route('/likeArtiste')
def likeArtiste():
    """
    Cette fonction permet de "liker" un artiste, c'est à dire l'ajouter aux favoris. Même fonctionnement que likeAlbum().
    
    """
    
    connexion = sqlite3.connect('Music_db.db')
    curseur = connexion.cursor()
    artisteID = request.args.get('artisteID')

    curseur.execute("""UPDATE ARTISTE
                       SET isLiked = "true"
                       WHERE idArtistes = (?)""", (artisteID,))
    
    connexion.commit()
    
    curseur.execute("""SELECT Pseudo, Nom, Prenom, GenreName, Daybirth, ARTISTE.isLiked, pic_url
                    FROM ARTISTE
                    JOIN GENRE ON ARTISTE.Genre = GENRE.idGenre
                    WHERE ARTISTE.idArtistes = (?)""", (artisteID,))
    
    
    elements = curseur.fetchall()
    
    return render_template('artiste.html', elements=elements, artisteID=artisteID)


@app.route('/notLikeArtiste')
def notLikeArtiste():
    """
    Cette fonction permet de supprimer son like d'un artiste, c'est à dire l'enlever des favoris. Même fonctionnement que notLikeAlbum()
    
    """
    
    connexion = sqlite3.connect('Music_db.db')
    curseur = connexion.cursor()
    artisteID = request.args.get('artisteID')

    curseur.execute("""UPDATE ARTISTE
                       SET isLiked = "False"
                       WHERE idArtistes = (?)""", (artisteID,))
    connexion.commit()
    curseur.execute("""SELECT Pseudo, Nom, Prenom, GenreName, Daybirth, ARTISTE.isLiked, pic_url
                    FROM ARTISTE
                    JOIN GENRE ON ARTISTE.Genre = GENRE.idGenre
                    WHERE ARTISTE.idArtistes = (?)""", (artisteID,))
    
    elements = curseur.fetchall()
    
    return render_template('artiste.html', elements=elements, artisteID=artisteID)


@app.route('/editArtiste')
def editArtiste():
    """
    Cette fonction permet d'afficher la page de modifications des informations d'un artiste
    
    """
    artisteID = request.args.get('artisteID') # On récupère de quel artiste il s'agit
    connexion = sqlite3.connect('Music_db.db')
    curseur = connexion.cursor()

    curseur.execute("""SELECT Pseudo, Nom, Prenom, GenreName, Daybirth, idArtistes
                        FROM ARTISTE
                        JOIN GENRE ON ARTISTE.Genre = GENRE.idGenre
                        WHERE ARTISTE.idArtistes = (?)""", (artisteID,)) # On récupère ces informations pour les placer en guise d'exemple dans le "placeholder" de l'HTML.
                                                                         # c'est à dire le texte en "fond" d'une saisie de texte

    elements = curseur.fetchall()
    
    return render_template('editArtiste.html', elements=elements)


@app.route('/album')
def album():
    """
    Cette fonction permet d'afficher les données sur un album en particulier, en fonction de son ID.
    Données récupérées : id, Nom, Date de sortie, Nombre de morceaux, Genre, Pseudo de l'artiste, s'il est liké, sa couverture
    
    """
    
    albumID = request.args.get('albumID')
    connexion = sqlite3.connect('Music_db.db')
    curseur = connexion.cursor()
    curseur.execute("""SELECT idAlbum, ALBUMS.Nom, DateSortie, NbrMorceaux, GenreName, ARTISTE.Pseudo, ALBUMS.isLiked, cover_url
                                  FROM ALBUMS
                                  JOIN GENRE ON ALBUMS.idGenre = GENRE.idGenre
                                  JOIN ARTISTE ON ALBUMS.idArtiste = ARTISTE.idArtistes
                                  WHERE ALBUMS.idAlbum = (?)""", (albumID,))
    
    elements = curseur.fetchall()
    
    return render_template('album.html', elements=elements, albumID=albumID)


@app.route('/editAlbum')
def editAlbum():
    """
    Cette fonction permet d'afficher la page de modifications des informations d'un album. Même fonctionnement que editArtiste()
    
    """
    albumID = request.args.get('albumID')
    connexion = sqlite3.connect('Music_db.db')
    curseur = connexion.cursor()
    curseur.execute("""SELECT idAlbum, ALBUMS.Nom, DateSortie, NbrMorceaux, GenreName, ARTISTE.Pseudo, idArtiste
                                  FROM ALBUMS
                                  JOIN GENRE ON ALBUMS.idGenre = GENRE.idGenre
                                  JOIN ARTISTE ON ALBUMS.idArtiste = ARTISTE.idArtistes
                                  WHERE ALBUMS.idAlbum = (?)""", (albumID,))
    
    elements = curseur.fetchall()
    
    return render_template('editAlbum.html', elements=elements, albumID=albumID)


@app.route('/deleteAlbum')
def deleteAlbum():
    """
    Cette fonction permet d'afficher la page pour supprimer d'un album, en fonction de son ID
    
    """
    albumID = request.args.get('albumID')
    connexion = sqlite3.connect('Music_db.db')
    curseur = connexion.cursor()
    
    curseur.execute("""SELECT Nom
                       FROM ALBUMS 
                       WHERE idAlbum = (?)""", (albumID,)) # Ce SELECT permet juste de récupérer le nom de l'album afin de le faire apparaître sur la page
    
    nomAlbum = curseur.fetchone()[0]

    return render_template('deleteAlbum.html', albumID=albumID, nomAlbum=nomAlbum)


@app.route('/deleteRecALBUM', methods=['POST', 'GET'])
def deleteRecALBUM():
    """
    Cette fonction permet de supprimer un album de la bdd.
    
    """
    msg = '' # on définit le message de réussite ou d'échec
    if request.method == 'POST':
        try:
            albumID = request.form['albumID'] # on récupère l'id de l'album

            with sqlite3.connect('Music_db.db') as connexion:
                curseur = connexion.cursor()
                curseur.execute("""DELETE
                                    FROM ALBUMS
                                    WHERE idAlbum = (?)""", (albumID,)) #on le supprime
                
                connexion.commit()
                
                msg = "Album correctement supprimé !" # Le message qui sera affiché montrant la réussite de l'action
                
                connexion.close()
        
        except: # S'il y a une erreur
            connexion.rollback()
            msg = 'Erreur lors de la suppresion' # Le message qui sera affiché montrant qu'il y a eu un problème
            connexion.close()
        finally:
            return render_template('result.html', msg=msg)
              
              
@app.route('/editrecALBUM', methods=["POST", "GET"])
def editrecALBUM():
    """
    Cette fonction permet modifier les informations d'un album    
    """
    
    msg = ''
    
    if request.method == 'POST':
        try:
            
            # On récupère les valeurs que l'utilisateur a entré (ou non, dans ce cas la valeur sera égale à '' et sera traitée après)
            Nom = request.form["nom_album"]
            DateSortie = request.form["datesortie"]
            NbrMorceaux = request.form["nbrMorceaux"]
            Genre = request.form["genre-type-album"]

            # valeur par défaut, celle déjà enregistrée dans la base de données qui sont récupérés grâce à des input désactivés, donc invisible pour l'utilisateur
            albumID = request.form["albumID"]
            artisteID = request.form["artisteID"]
            Nom_default = request.form["nom_default"]
            DateSortie_default = request.form["datesortie_default"]
            NbrMorceaux_default = request.form["nbrMorceaux_default"]
            Genre_default = request.form["genre-type-album_default"]

            # Si l'utilisateur n'a rien entré dans une des cases, alors la valeur "par défaut", qui était déjà présente donc, n'est pas remplacée par une autre mais par elle-même.
            if Nom == "":
                Nom = Nom_default
            if DateSortie == "":
                DateSortie = DateSortie_default
            if NbrMorceaux == "":
                NbrMorceaux = NbrMorceaux_default
            if Genre == "":
                Genre = Genre_default

            with sqlite3.connect('Music_db.db') as connexion:
                
                curseur = connexion.cursor()
                curseur.execute("""UPDATE ALBUMS
                                   SET Nom = (?), DateSortie = (?), NbrMorceaux = (?), idGenre = (?) 
                                   WHERE idAlbum = (?)""", (Nom, DateSortie, NbrMorceaux, Genre, albumID)) # Mise à jour avec les nouvelles valeurs

                connexion.commit()
                msg = "Modifications prises en compte !" # Message de réussite
                connexion.close()
        except:
            connexion.rollback()
            msg = 'Erreur lors de la modification' # Message d'erreur
            connexion.close()
        finally:
            return render_template('result.html', msg=msg) # on affiche la page 'result.html' qui affiche seulement si l'action à réussit ou non
        

@app.route('/editrec', methods=["POST", "GET"])
def editrect():
    """
    Cette fonction permet de modifier les informations d'un artiste.
    
    """
    msg = ''
    if request.method == 'POST':
        try:
            
            # Valeurs entrées par l'utilisateur
            Nom = request.form["artist-last-name"]
            Prenom = request.form["artist-first-name"]
            Genre = request.form["genre-type"]
            Pseudo = request.form["pseudo"]
            Daybirth = request.form["daybirth"]
            
            # valeurs par défaut
            artisteID = request.form.get('artisteID')
            Nom_default = request.form.get('artist-last-name_default')
            Prenom_default = request.form.get('artist-first-name_default')
            Pseudo_default = request.form.get('pseudo_default')
            Daybirth_default = request.form.get('daybirth_default')
            
            # Si l'utilisateur n'a rien entré dans une des cases, alors la valeur "par défaut", qui était déjà présente donc, n'est pas remplacée par une autre mais par elle-même.
            if Nom == "":
                Nom = Nom_default
            if Prenom == "":
                Prenom = Prenom_default
            if Pseudo == "":
                Pseudo = Pseudo_default
            if Daybirth == "":
                Daybirth = Daybirth_default
            
            with sqlite3.connect('Music_db.db') as connexion:
                
                curseur = connexion.cursor()
                curseur.execute("""UPDATE ARTISTE
                                    SET Nom = (?), Prenom = (?), Genre = (?), Pseudo = (?), Daybirth = (?)
                                    WHERE idArtistes = (?)""", (Nom, Prenom, Genre, Pseudo, Daybirth, artisteID,)) # Mise à jour de la bdd
                
                connexion.commit()
                msg = "Modifications prises en compte !" # Message de réussite
                connexion.close()
        except:
            connexion.rollback()
            msg = 'Erreur lors de la modification' # Message d'erreur
            connexion.close()
        finally:
            return render_template('result.html', msg=msg) # affichage du résultat de la requête


@app.route('/addrec', methods=["POST", "GET"])
def addrec():
    """
    Cette fonction permet d'ajouter un album à la bdd
    
    """
    msg = ''
    
    if request.method == 'POST':
        try:
            
            # Récupération des informations données par l'utilisateur
            Nom = request.form["albumName"]
            DateSortie = request.form["dateDeSortie"]           
            NbrMorceaux = request.form["nbrMorceaux"]
            idGenre = request.form["genre-type"]
            idArtiste = request.form["artist-name"]

            with sqlite3.connect('Music_db.db') as connexion:

                curseur = connexion.cursor()
                curseur.execute("SELECT Pseudo FROM ARTISTE") # On récupère tous les pseudos des artistes
                liste_tempo = curseur.fetchall() # On les mets dans une liste temporaire
                
                correspondance_find = False # On définit correspondance_find sur False

                name_artist = idArtiste # idArtiste à ce moment est égal au string que l'utilisateur a entré, pour le sauvegarder, on le met dans une variable name_artist
                
                # On range tous les noms d'artiste dans une seule liste (cela évite les tuples qui sont renvoyés par le .fetchall())
                liste_artiste = [] 
                for artist in liste_tempo:
                    liste_artiste.append(artist[0])
                
                
                # Ici, on va vérifier si l'artiste que l'utilisateur a entré est déjà présent ou non dans la base de données
                for i in liste_artiste:
                    ratio = fuzz.ratio(idArtiste.casefold(), i.casefold()) # on admet le "ratio" de ressemblance entre ce qu'a entré l'utilisateur (idArtiste) mis en minuscule et chaque Pseudo d'artiste, mis en minuscule de la liste "liste_artiste"
                    if ratio >= 90: # si ce ratio est supérieur ou égal à 90 / Si le taux de ressemblance est d'au moins 90%, on peut considérer que c'est le même artiste
                        correspondance_find = True # il y a correspondance
                        curseur.execute("SELECT idArtistes FROM ARTISTE WHERE Pseudo = ?", (i,)) # on cherche l'id correspondant
                        idArtiste = int(curseur.fetchone()[0]) # idArtiste devient vraiment l'id de l'artiste entré.
                        break; 
                        
                                 
                if correspondance_find == False: # Si aucune correspondance n'a été trouvée
                    curseur.execute("INSERT INTO ARTISTE (Genre, Pseudo) VALUES (?, ?)", (idGenre, name_artist,)) # on créé un nouvel artiste avec le nom qu'a entré l'utilisateur
                    connexion.commit()
                    curseur.execute("SELECT idArtistes FROM ARTISTE WHERE Pseudo = ?", (name_artist,)) # puis on récupère son (nouvel) id
                    idArtiste = curseur.fetchone()[0]
                
                
                ###### Récupération par API de la photo de profil de l'artiste ########
                
                client_access_token = api_key.client_access_token

                url = f"https://api.genius.com/search?q={name_artist}&access_token={client_access_token}"
                response = requests.get(url)
                data = response.json() # on récupère les réponses de l'api en json
                
                # ID genius de l'artiste
                artist_id = data["response"]["hits"][0]["result"]["primary_artist"]["id"]
                
                url = f"https://api.genius.com/artists/{artist_id}?access_token={client_access_token}"
                response = requests.get(url)
                
                # Analyse de la réponse JSON
                data = response.json()

                # Photo de profil de l'artiste
                image_url = data["response"]["artist"]["image_url"]
                
                curseur.execute("""UPDATE ARTISTE 
                                SET pic_url = (?)
                                WHERE idArtistes = (?)""", (image_url, idArtiste,)) # on ajoute l'url de la photo de profil à l'artiste
               
                 
                ###### FIN DE LA Récupération ########


                
                ##### Récupération de la cover de l'abum ######
                
                API_KEY = "cle-api-lastFM" # votre clé API lastfm
                url = f"https://ws.audioscrobbler.com/2.0/?method=album.search&api_key={API_KEY}&album={Nom.replace(' ', '%20')}&artist={name_artist}&format=json"
                response = requests.get(url)
                data = response.json() # on récupère la réponse de l'api en json

                album = data["results"]["albummatches"]["album"][0] # on trouve l'album
                albumCover = album["image"][3]["#text"] # puis l'url de la photo
                

                ###### FIN DE LA Récupération ########

                
                curseur.execute("INSERT INTO ALBUMS (Nom, DateSortie, NbrMorceaux, idGenre, idArtiste, cover_url) VALUES (?, ?, ?, ?, ?, ?)", (Nom, DateSortie, NbrMorceaux, idGenre, idArtiste, albumCover,)) # On ajoute l'album à la bdd avec les informations
                connexion.commit()
                msg = "Album correctement ajouté !" # Message de succès
                connexion.close()
        
        except:
            connexion.rollback()
            msg = "Une erreur est survenue" # Message d'erreur
            connexion.close()
            
        finally:
            return render_template('result.html', msg=msg) # on affiche le résultat

    
if __name__ == "__main__":
    app.run(host="0.0.0.0") # on run l'application avec un autre "host" (0.0.0.0) car cela m'évitait certains soucis en interne.
