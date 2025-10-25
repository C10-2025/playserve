from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from profil.models import Profile
from community.models import Community

DUMMY_TEMPLATES = {
    'main.html': (
        'MAIN '
        '{% if profile %}HAS_PROFILE{% else %}NO_PROFILE{% endif %} '
        '{% if is_admin_access %}ADMIN{% else %}NONADMIN{% endif %}'
    )
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


class MainViewBase(TestCase):
    def setUp(self):
        self._tmpl_cm = self.settings(TEMPLATES=OVERRIDDEN_TEMPLATES)
        self._tmpl_cm.__enter__()
        self.client = Client()
        self.normal_user = User.objects.create_user(username='u1', password='pass')
        self.admin_user = User.objects.create_user(username='u2', password='pass')
        self.super_user = User.objects.create_superuser(username='super', password='pass', email='s@example.com')
        self.profile_user, _ = Profile.objects.get_or_create(user=self.normal_user, defaults={'role': 'USER'})
        if self.profile_user.role != 'USER':
            self.profile_user.role = 'USER'
            self.profile_user.save()
        self.profile_admin, _ = Profile.objects.get_or_create(user=self.admin_user, defaults={'role': 'ADMIN'})
        if self.profile_admin.role != 'ADMIN':
            self.profile_admin.role = 'ADMIN'
            self.profile_admin.save()
        self.profile_super, _ = Profile.objects.get_or_create(user=self.super_user, defaults={'role': 'USER'})
        self.c1 = Community.objects.create(name='C1', description='d', creator=self.admin_user)
        self.c2 = Community.objects.create(name='C2', description='d', creator=self.super_user)

    def tearDown(self):
        self._tmpl_cm.__exit__(None, None, None)


class MainViewAnonymousTests(MainViewBase):
    def test_home_anonymous(self):
        resp = self.client.get(reverse('main:home'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('profile', resp.context)
        self.assertNotIn('is_admin_access', resp.context)
        self.assertNotIn('total_users', resp.context)
        self.assertNotIn('total_community', resp.context)


class MainViewAuthenticatedNonAdminTests(MainViewBase):
    def test_home_authenticated_non_admin(self):
        self.client.login(username='u1', password='pass')
        resp = self.client.get(reverse('main:home'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('profile', resp.context)
        self.assertEqual(resp.context['profile'], self.profile_user)
        self.assertIn('is_admin_access', resp.context)
        self.assertFalse(resp.context['is_admin_access'])
        self.assertNotIn('total_users', resp.context)
        self.assertNotIn('total_community', resp.context)


class MainViewAuthenticatedBizAdminTests(MainViewBase):
    def test_home_authenticated_biz_admin_role(self):
        self.client.login(username='u2', password='pass')
        resp = self.client.get(reverse('main:home'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('profile', resp.context)
        self.assertEqual(resp.context['profile'], self.profile_admin)
        self.assertTrue(resp.context.get('is_admin_access'))
        self.assertIn('total_users', resp.context)
        self.assertIn('total_community', resp.context)
        self.assertEqual(resp.context['total_users'], User.objects.count())
        self.assertEqual(resp.context['total_community'], Community.objects.count())


class MainViewAuthenticatedSuperuserTests(MainViewBase):
    def test_home_authenticated_superuser(self):
        self.client.login(username='super', password='pass')
        resp = self.client.get(reverse('main:home'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('profile', resp.context)
        self.assertEqual(resp.context['profile'], self.profile_super)
        self.assertTrue(resp.context.get('is_admin_access'))
        self.assertEqual(resp.context['total_users'], User.objects.count())
        self.assertEqual(resp.context['total_community'], Community.objects.count())


class MainViewProfileDoesNotExistTests(MainViewBase):
    def test_home_authenticated_without_profile(self):
        up = User.objects.create_user(username='noprof', password='pass')
        Profile.objects.filter(user=up).delete()
        self.client.login(username='noprof', password='pass')
        resp = self.client.get(reverse('main:home'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('profile', resp.context)
        self.assertIsNone(resp.context['profile'])
        self.assertIn('is_admin_access', resp.context)
        self.assertFalse(resp.context['is_admin_access'])
        self.assertNotIn('total_users', resp.context)
        self.assertNotIn('total_community', resp.context)
