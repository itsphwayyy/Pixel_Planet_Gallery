import datetime
import json
import os
import random
import string
from bs4 import BeautifulSoup
from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

# Folder configuration
UPLOAD_FOLDER = 'static/uploads'
DATA_FILE = 'gallery_data.json'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# --- DATA STORAGE HELPER FUNCTIONS ---
def load_data():
  """Loads codes and active artists from JSON file."""
  if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
      return json.load(f)
  return {'codes': {}, 'artists': []}


def save_data(data):
  """Saves codes and active artists to JSON file."""
  with open(DATA_FILE, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4)


def check_and_remove_expired_artists():
  """Checks if any artist's countdown duration has expired.

  If expired, removes them from the JSON database and updates HTML files automatically.
  """
  data = load_data()
  current_time = datetime.datetime.now().timestamp()

  active_artists = []
  expired_found = False

  for artist in data['artists']:
    if artist['expires_at'] > current_time:
      active_artists.append(artist)
    else:
      expired_found = True

  if expired_found:
    data['artists'] = active_artists
    save_data(data)
    rebuild_website_files(active_artists)


def rebuild_website_files(active_artists):
  """Rebuilds templates/artist.html and templates/gallery.html to remove expired artists."""
  # 1. Update artist.html
  with open('templates/artist.html', 'r', encoding='utf-8') as f:
    soup_artist = BeautifulSoup(f, 'html.parser')

  artist_grid = soup_artist.find('div', class_='row g-4 justify-content-center')
  if artist_grid:
    # Retain initial hardcoded artists or rebuild dynamically
    # Re-appending current active subscription artists
    for artist in active_artists:
      name = artist['name']
      bio = artist['bio']
      p_img = artist['profile_img']

      card_html = f"""
            <div class="col-lg-4 col-md-6">
                <div class="profile-card text-center p-0">
                  <div class="card-banner" style="background-color: #6cc070;"></div>
                  <div class="avatar-wrapper">
                    <img src="{p_img}" alt="{name}" class="avatar-img" style="border-color: #6cc070;">
                  </div>
                  <div class="px-4 pt-3 pb-4">
                    <h3 class="artist-name text-uppercase mb-1">{name}</h3>
                    <p class="artist-track text-uppercase mb-3">Featured Artist</p>
                    <p class="artist-bio-text mb-4">{bio}</p>
                    <a href="gallery.html#artwork-{name.lower().replace(' ', '-')}" class="btn btn-outline-dark btn-sm rounded-pill px-4 py-2">View Artwork</a>
                  </div>
                </div>
            </div>
            """
      artist_grid.append(BeautifulSoup(card_html, 'html.parser'))

    with open('templates/artist.html', 'w', encoding='utf-8') as f:
      f.write(str(soup_artist))

  # 2. Update gallery.html
  with open('templates/gallery.html', 'r', encoding='utf-8') as f:
    soup_gallery = BeautifulSoup(f, 'html.parser')

  main_container = soup_gallery.find('main').find('div', class_='container')
  if main_container:
    for artist in active_artists:
      name = artist['name']
      art_title = artist['art_title']
      art_medium = artist['art_medium']
      art_img = artist['art_img']

      gallery_html = f"""
            <div class="mb-5" id="artwork-{name.lower().replace(' ', '-')}">
              <h4 class="fw-bold text-uppercase mb-4 pb-2 border-bottom border-dark" style="letter-spacing: 1px; font-size: 1.1rem;">{name}'s Artwork Collection</h4>
              <div class="row g-4">
                <div class="col-lg-6">
                  <div class="gallery-exhibit-pair">
                    <div class="museum-frame-card">
                      <div class="mat-board">
                        <img src="{art_img}" alt="{art_title}" class="artwork-img-portrait">
                      </div>
                    </div>
                    <div class="gallery-label-card">
                      <p class="gallery-label-title">{art_title}</p>
                      <p class="gallery-label-artist">{name}</p>
                      <p class="gallery-label-medium">{art_medium} • 2026</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            """
      main_container.append(BeautifulSoup(gallery_html, 'html.parser'))

    with open('templates/gallery.html', 'w', encoding='utf-8') as f:
      f.write(str(soup_gallery))


# --- ROUTE HANDLERS ---
@app.route('/')
def home():
  check_and_remove_expired_artists()
  return render_template('index.html')


@app.route('/artist.html')
def artists():
  check_and_remove_expired_artists()
  return render_template('artist.html')


@app.route('/gallery.html')
def gallery():
  check_and_remove_expired_artists()
  return render_template('gallery.html')


@app.route('/contact.html')
def contact():
  return render_template('contact.html')


# --- ADMIN PANEL ---
@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
  check_and_remove_expired_artists()
  data = load_data()
  message = None

  if request.method == 'POST':
    try:
      months = int(request.form.get('months'))
      code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
      data['codes'][code] = {'months': months}
      save_data(data)
      message = (
          f'Generated Access Code: <strong>{code}</strong> for {months}'
          ' month(s)!'
      )
    except ValueError:
      message = 'Please enter a valid number of months.'

  # Calculate countdown for display
  current_time = datetime.datetime.now().timestamp()
  active_artists = []
  for artist in data['artists']:
    time_left = artist['expires_at'] - current_time
    if time_left > 0:
      days_left = int(time_left // 86400)
      artist['time_remaining'] = f'{days_left} days left'
    else:
      artist['time_remaining'] = 'Expired'
    active_artists.append(artist)

  return render_template(
      'admin.html',
      codes=data['codes'],
      artists=active_artists,
      message=message,
  )


# --- USER SUBMISSION PORTAL ---
@app.route('/submit', methods=['GET', 'POST'])
def submit_portal():
  check_and_remove_expired_artists()
  error = None
  data = load_data()

  if request.method == 'POST':
    code = request.form.get('access_code', '').strip().upper()

    if code in data['codes']:
      months = data['codes'][code]['months']

      # Remove code immediately upon use
      del data['codes'][code]

      name = request.form.get('name')
      bio = request.form.get('bio')
      art_title = request.form.get('art_title')
      art_medium = request.form.get('art_medium')

      # Upload profile image
      profile_file = request.files['profile_photo']
      profile_filename = f"profile_{name.lower().replace(' ', '_')}.jpg"
      profile_path = os.path.join(
          app.config['UPLOAD_FOLDER'], profile_filename
      )
      profile_file.save(profile_path)

      # Upload artwork image
      art_file = request.files['art_photo']
      art_filename = f"art_{name.lower().replace(' ', '_')}.jpg"
      art_path = os.path.join(app.config['UPLOAD_FOLDER'], art_filename)
      art_file.save(art_path)

      # Calculate expiration timestamp (30 days per month)
      duration_seconds = months * 30 * 86400
      expires_at = datetime.datetime.now().timestamp() + duration_seconds

      # Save new artist record
      new_artist = {
          'name': name,
          'bio': bio,
          'profile_img': f'static/uploads/{profile_filename}',
          'art_title': art_title,
          'art_medium': art_medium,
          'art_img': f'static/uploads/{art_filename}',
          'months': months,
          'expires_at': expires_at,
      }
      data['artists'].append(new_artist)
      save_data(data)

      # Append directly to HTML pages
      rebuild_website_files(data['artists'])

      return render_template('success.html', name=name, months=months)
    else:
      error = (
          'Invalid or already used access code. Please check with the gallery'
          ' admin.'
      )

  return render_template('submit.html', error=error)


if __name__ == '__main__':
  app.run(debug=True)
