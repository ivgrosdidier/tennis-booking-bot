from flask import Blueprint, request, redirect, url_for, flash, session
from extensions import db
from helpers.players import check_name_in_club_directory
from routes.auth import auth_required, get_current_uid
import random, string

partners_bp = Blueprint('partners', __name__)


@partners_bp.route('/add-partner', methods=['POST'])
@auth_required
def add_partner():
    uid = get_current_uid()
    full_name = request.form.get('full_name').strip().title()
    nickname  = request.form.get('nickname').strip().title()

    if full_name and nickname:
        if not check_name_in_club_directory(full_name):
            flash(f'"{full_name}" not found in club directory. Check spelling.', 'error')
            return redirect(url_for('dashboard.dashboard'))

        ref = db.collection('users').document(uid).collection('partners')

        if ref.where('full_name', '==', full_name).get():
            flash(f'"{full_name}" already has a nickname.', 'error')
            return redirect(url_for('dashboard.dashboard'))

        if ref.where('nickname', '==', nickname).get():
            flash('Nickname already exists.', 'error')
            return redirect(url_for('dashboard.dashboard'))

        ref.add({
            'partner_id': ''.join(random.choices(string.ascii_uppercase + string.digits, k=3)),
            'full_name':  full_name,
            'nickname':   nickname
        })
        flash('Partner added!', 'success')

    return redirect(url_for('dashboard.dashboard'))


@partners_bp.route('/edit-partner/<partner_id>', methods=['POST'])
@auth_required
def edit_partner(partner_id):
    uid      = get_current_uid()
    new_name = request.form.get('full_name').strip().title()
    new_nick = request.form.get('nickname').strip().title()

    if not check_name_in_club_directory(new_name):
        flash(f'"{new_name}" not found in club directory. Check spelling.', 'error')
        return redirect(url_for('dashboard.dashboard'))

    ref = db.collection('users').document(uid).collection('partners')

    for doc in ref.where('full_name', '==', new_name).get():
        if doc.id != partner_id:
            flash(f'"{new_name}" already has a nickname.', 'error')
            return redirect(url_for('dashboard.dashboard'))

    for doc in ref.where('nickname', '==', new_nick).get():
        if doc.id != partner_id:
            flash('Nickname already in use.', 'error')
            return redirect(url_for('dashboard.dashboard'))

    ref.document(partner_id).update({'full_name': new_name, 'nickname': new_nick})
    flash('Partner updated!', 'success')
    return redirect(url_for('dashboard.dashboard'))


@partners_bp.route('/delete-partner/<partner_id>', methods=['POST'])
@auth_required
def delete_partner(partner_id):
    uid = get_current_uid()
    db.collection('users').document(uid).collection('partners').document(partner_id).delete()
    flash('Partner removed.', 'success')
    return redirect(url_for('dashboard.dashboard'))