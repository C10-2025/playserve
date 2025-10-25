from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from profil.models import Profile

DUMMY_TEMPLATES = {
    'register1.html': 'STEP1',
    'register2.html': 'STEP2',
    'login.html': 'LOGIN',
    'profile_update.html': 'PROFILE UPDATE',
    'admin_profile.html': 'ADMIN USERS',
}

OVERRIDDEN_TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': False,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
        'loaders': [
            ('django.template.loaders.locmem.Loader', DUMMY_TEMPLATES),
        ],
    },
}]

class BaseSetup(TestCase):
    def setUp(self):
        self._tmpl_cm = self.settings(TEMPLATES=OVERRIDDEN_TEMPLATES)
        self._tmpl_cm.__enter__()
        self.client = Client()
        self.user = User.objects.create_user(username='u1', password='pass')
        self.admin = User.objects.create_superuser(username='admin', password='pass', email='a@a.a')

    def tearDown(self):
        self._tmpl_cm.__exit__(None, None, None)


class RegisterStep1Tests(BaseSetup):
    def test_get(self):
        resp = self.client.get(reverse('profil:register1'))
        self.assertEqual(resp.status_code, 200)

    def test_post_success_sets_session_and_json(self):
        resp = self.client.post(reverse('profil:register1'), {'username': 'newuser', 'password': 'x', 'password2': 'x'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'success')
        session = self.client.session
        self.assertIn('registration_data', session)
        self.assertEqual(session['registration_data']['username'], 'newuser')

    def test_post_username_taken(self):
        User.objects.create_user(username='taken', password='p')
        resp = self.client.post(reverse('profil:register1'), {'username': 'taken', 'password': 'x', 'password2': 'x'})
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('username', data['errors'])

    def test_post_password_mismatch(self):
        resp = self.client.post(reverse('profil:register1'), {'username': 'abc', 'password': 'a', 'password2': 'b'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('password2', resp.json()['errors'])


class RegisterStep2Tests(BaseSetup):
    def test_redirect_if_no_session(self):
        resp = self.client.get(reverse('profil:register2'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('profil:register1'))

    def test_post_success_creates_user_updates_profile_logs_in_and_clears_session(self):
        session = self.client.session
        session['registration_data'] = {'username': 'newbie', 'password': 'pass123'}
        session.save()
        payload = {'lokasi': 'Bogor', 'instagram': 'iguser', 'avatar': 'image/avatar2.svg'}
        resp = self.client.post(reverse('profil:register2'), payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(User.objects.filter(username='newbie').exists())
        u = User.objects.get(username='newbie')
        self.assertTrue(hasattr(u, 'profile'))
        self.assertEqual(u.profile.lokasi, 'Bogor')
        self.assertEqual(u.profile.instagram, 'iguser')
        self.assertEqual(u.profile.avatar, 'image/avatar2.svg')
        resp2 = self.client.get(reverse('profil:register2'))
        self.assertEqual(resp2.status_code, 302)
        self.assertEqual(resp2.url, reverse('profil:register1'))

    def test_post_username_already_taken(self):
        User.objects.create_user(username='dupe', password='x')
        session = self.client.session
        session['registration_data'] = {'username': 'dupe', 'password': 'x'}
        session.save()
        payload = {'lokasi': 'Jakarta', 'instagram': '', 'avatar': 'image/avatar1.svg'}
        resp = self.client.post(reverse('profil:register2'), payload)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['status'], 'error')

    def test_post_invalid_form(self):
        session = self.client.session
        session['registration_data'] = {'username': 'badform', 'password': 'x'}
        session.save()
        payload = {'lokasi': 'Konoha', 'instagram': '', 'avatar': 'image/avatar1.svg'}
        resp = self.client.post(reverse('profil:register2'), payload)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['status'], 'error')
        self.assertIn('lokasi', resp.json()['errors'])


class LoginLogoutTests(BaseSetup):
    def test_login_get(self):
        resp = self.client.get(reverse('profil:login'))
        self.assertEqual(resp.status_code, 200)

    def test_login_success(self):
        resp = self.client.post(reverse('profil:login'), {'username': 'u1', 'password': 'pass'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'success')

    def test_login_invalid(self):
        resp = self.client.post(reverse('profil:login'), {'username': 'u1', 'password': 'wrong'})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()['status'], 'error')

    def test_logout_redirects_home(self):
        self.client.login(username='u1', password='pass')
        resp = self.client.get(reverse('profil:logout'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('main:home'))


class ProfileUpdateTests(BaseSetup):
    def test_requires_login(self):
        resp = self.client.get(reverse('profil:profile_update'))
        self.assertEqual(resp.status_code, 302)

    def test_get_form(self):
        self.client.login(username='u1', password='pass')
        resp = self.client.get(reverse('profil:profile_update'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('form', resp.context)

    def test_post_success(self):
        self.client.login(username='u1', password='pass')
        payload = {'lokasi': 'Depok', 'instagram': 'newig', 'avatar': 'image/avatar3.svg'}
        resp = self.client.post(reverse('profil:profile_update'), payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'success')
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.lokasi, 'Depok')
        self.assertEqual(self.user.profile.instagram, 'newig')
        self.assertEqual(self.user.profile.avatar, 'image/avatar3.svg')

    def test_post_invalid(self):
        self.client.login(username='u1', password='pass')
        payload = {'lokasi': 'Atlantis', 'instagram': 'x', 'avatar': 'image/avatar3.svg'}
        resp = self.client.post(reverse('profil:profile_update'), payload)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['status'], 'error')
        self.assertIn('lokasi', resp.json()['errors'])


class AdminGuardTests(BaseSetup):
    def test_manage_users_requires_admin(self):
        self.client.login(username='u1', password='pass')
        resp = self.client.get(reverse('profil:manage_users'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, f"/?next={reverse('profil:manage_users')}")

    def test_manage_users_admin_ok_and_search(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.get(reverse('profil:manage_users'))
        self.assertEqual(resp.status_code, 200)
        resp_q = self.client.get(reverse('profil:manage_users'), {'q': 'u1'})
        self.assertEqual(resp_q.status_code, 200)

    def test_delete_user_requires_admin(self):
        self.client.login(username='u1', password='pass')
        resp = self.client.post(reverse('profil:delete_user', args=[self.admin.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, f"/?next={reverse('profil:delete_user', args=[self.admin.id])}")

    def test_delete_user_invalid_method(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.get(reverse('profil:delete_user', args=[self.user.id]))
        self.assertEqual(resp.status_code, 405)

    def test_delete_user_cannot_delete_self(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.post(reverse('profil:delete_user', args=[self.admin.id]))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()['status'], 'error')

    def test_delete_user_success(self):
        self.client.login(username='admin', password='pass')
        target = User.objects.create_user(username='victim', password='p')
        resp = self.client.post(reverse('profil:delete_user', args=[target.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'success')
        self.assertFalse(User.objects.filter(id=target.id).exists())
