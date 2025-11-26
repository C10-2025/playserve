from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages

from community.models import Community, Post, Reply

DUMMY_TEMPLATES = {
    'discover_communities.html': '{% for c in communities %}{{ c.name }} {% endfor %}',
    'my_communities.html': '{% for c in communities %}{{ c.name }} {% endfor %}',
    'community_detail.html': '{% for p in posts %}{{ p.title }} {% endfor %}',
    'create_community.html': 'FORM CREATE',
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

        self.user = User.objects.create_user(username='user', password='pass')
        self.staff = User.objects.create_user(username='staff', password='pass', is_staff=True)
        self.super = User.objects.create_superuser(username='super', password='pass', email='s@x.com')

        self.comm_by_staff = Community.objects.create(
            name='DjangoID', description='desc', creator=self.staff
        )
        self.comm_by_super = Community.objects.create(
            name='PyJakarta', description='desc', creator=self.super
        )

        self.comm_by_staff.members.add(self.user)
        self.post1 = Post.objects.create(
            community=self.comm_by_staff, author=self.user, title='Hello', content='World'
        )
        self.reply1 = Reply.objects.create(
            post=self.post1, author=self.user, content='Nice!'
        )

    def tearDown(self):
        self._tmpl_cm.__exit__(None, None, None)

class DiscoverCommunitiesTests(BaseSetup):
    def test_requires_login(self):
        resp = self.client.get(reverse('discover_communities'))
        self.assertEqual(resp.status_code, 302) 

    def test_list_all_and_context(self):
        self.client.login(username='user', password='pass')
        resp = self.client.get(reverse('discover_communities'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('communities', resp.context)
        self.assertIn(self.comm_by_staff, resp.context['communities'])
        self.assertIn('joined_community_ids', resp.context)
        self.assertIn(self.comm_by_staff.id, list(resp.context['joined_community_ids']))

    def test_search_query(self):
        self.client.login(username='user', password='pass')
        resp = self.client.get(reverse('discover_communities'), {'q': 'PyJak'})
        self.assertEqual(resp.status_code, 200)
        communities = list(resp.context['communities'])
        self.assertIn(self.comm_by_super, communities)
        self.assertNotIn(self.comm_by_staff, communities)


class MyCommunitiesTests(BaseSetup):
    def test_non_admin_sees_joined(self):
        self.client.login(username='user', password='pass')
        resp = self.client.get(reverse('my_communities'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['mode'], 'joined')
        self.assertIn(self.comm_by_staff, resp.context['communities'])
        self.assertNotIn(self.comm_by_super, resp.context['communities'])

    def test_admin_sees_created(self):
        self.client.login(username='staff', password='pass')
        resp = self.client.get(reverse('my_communities'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['mode'], 'created')
        self.assertIn(self.comm_by_staff, resp.context['communities'])
        self.assertNotIn(self.comm_by_super, resp.context['communities'])

class JoinCommunityTests(BaseSetup):
    def test_only_post_allowed(self):
        self.client.login(username='user', password='pass')
        url = reverse('join_community', args=[self.comm_by_super.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)
        self.assertJSONEqual(resp.content, {'error': 'Invalid request method'})

    def test_join_success(self):
        self.client.login(username='user', password='pass')
        url = reverse('join_community', args=[self.comm_by_super.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'joined')
        self.assertTrue(self.comm_by_super.members.filter(id=self.user.id).exists())

    def test_join_already_member(self):
        self.client.login(username='user', password='pass')
        url = reverse('join_community', args=[self.comm_by_staff.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'already_joined')

class CreateCommunityTests(BaseSetup):
    def test_requires_admin(self):
        self.client.login(username='user', password='pass')
        resp = self.client.get(reverse('create_community'))
        self.assertEqual(resp.status_code, 302)

    def test_get_form_admin(self):
        self.client.login(username='staff', password='pass')
        resp = self.client.get(reverse('create_community'))
        self.assertEqual(resp.status_code, 200)

    def test_name_required_html(self):
        self.client.login(username='staff', password='pass')
        resp = self.client.post(reverse('create_community'), {'name': ''}, follow=True)
        self.assertEqual(resp.status_code, 200)
        msgs = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertIn('Name is required.', msgs)

    def test_duplicate_name_ajax(self):
        self.client.login(username='staff', password='pass')
        url = reverse('create_community')
        resp = self.client.post(
            url,
            {'name': 'DjangoID', 'description': 'x'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json().get('code'), 'duplicate_name')

    def test_create_success_ajax(self):
        self.client.login(username='staff', password='pass')
        url = reverse('create_community')
        resp = self.client.post(
            url,
            {'name': 'NewComm', 'description': 'Nice'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get('status'), 'success')
        self.assertTrue(Community.objects.filter(name='NewComm', creator=self.staff).exists())

class UpdateCommunityTests(BaseSetup):
    def test_requires_admin(self):
        self.client.login(username='user', password='pass')
        url = reverse('update_community', args=[self.comm_by_staff.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

    def test_only_creator_can_update(self):
        self.client.login(username='super', password='pass')
        url = reverse('update_community', args=[self.comm_by_staff.id])
        resp = self.client.get(url, follow=True)
        msgs = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertIn("You can only edit your own communities.", msgs)

    def test_update_success_by_creator(self):
        self.client.login(username='staff', password='pass')
        url = reverse('update_community', args=[self.comm_by_staff.id])
        resp = self.client.post(url, {'name': 'DjangoID2', 'description': 'updated'}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.comm_by_staff.refresh_from_db()
        self.assertEqual(self.comm_by_staff.name, 'DjangoID2')
        msgs = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertTrue(any("updated successfully" in m for m in msgs))


class DeleteCommunityTests(BaseSetup):
    def test_only_creator_can_delete(self):
        self.client.login(username='super', password='pass')
        url = reverse('delete_community', args=[self.comm_by_staff.id])
        resp = self.client.get(url, follow=True)
        msgs = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertIn("You can only delete communities you created.", msgs)
        self.assertTrue(Community.objects.filter(id=self.comm_by_staff.id).exists())

    def test_delete_success_by_creator(self):
        self.client.login(username='staff', password='pass')
        url = reverse('delete_community', args=[self.comm_by_staff.id])
        resp = self.client.get(url, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Community.objects.filter(id=self.comm_by_staff.id).exists())
        msgs = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertIn("Community deleted successfully.", msgs)

class CommunityDetailTests(BaseSetup):
    def test_creator_auto_added_if_not_member(self):
        self.comm_by_super.members.remove(self.super)
        self.client.login(username='super', password='pass')
        url = reverse('community_detail', args=[self.comm_by_super.id])
        resp = self.client.get(url, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(self.comm_by_super.members.filter(id=self.super.id).exists())

    def test_non_member_redirect(self):
        self.client.login(username='staff', password='pass')
        url = reverse('community_detail', args=[self.comm_by_super.id])
        resp = self.client.get(url, follow=True)
        msgs = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertIn("You must join this community to see its posts.", msgs)

    def test_member_can_see_posts(self):
        self.client.login(username='user', password='pass')
        url = reverse('community_detail', args=[self.comm_by_staff.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('posts', resp.context)
        self.assertIn(self.post1, resp.context['posts'])


class CreatePostTests(BaseSetup):
    def test_must_be_member(self):
        self.client.login(username='staff', password='pass')
        url = reverse('create_post', args=[self.comm_by_staff.id])
        resp = self.client.post(url, {'title': 'x', 'content': 'y'}, follow=True)
        msgs = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertIn("You must join this community before posting.", msgs)

    def test_validation(self):
        self.client.login(username='user', password='pass')
        url = reverse('create_post', args=[self.comm_by_staff.id])
        resp = self.client.post(url, {'title': '', 'content': ''}, follow=True)
        msgs = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertIn("Both title and content are required.", msgs)

    def test_create_success(self):
        self.client.login(username='user', password='pass')
        url = reverse('create_post', args=[self.comm_by_staff.id])
        self.client.post(url, {'title': 'New', 'content': 'Post'}, follow=True)
        self.assertTrue(Post.objects.filter(title='New', community=self.comm_by_staff, author=self.user).exists())


class CreateReplyTests(BaseSetup):
    def test_must_be_member(self):
        self.client.login(username='staff', password='pass')
        url = reverse('create_reply', args=[self.post1.id])
        resp = self.client.post(url, {'content': 'hi'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('discover_communities'))

    def test_reply_created(self):
        self.client.login(username='user', password='pass')
        url = reverse('create_reply', args=[self.post1.id])
        resp = self.client.post(url, {'content': 'second'})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Reply.objects.filter(post=self.post1, author=self.user, content='second').exists())

    def test_ignore_blank(self):
        self.client.login(username='user', password='pass')
        url = reverse('create_reply', args=[self.post1.id])
        self.client.post(url, {'content': '   '})
        self.assertFalse(Reply.objects.filter(post=self.post1, author=self.user, content='   ').exists())

class DeleteContentAdminOnlyTests(BaseSetup):
    def test_delete_post_requires_admin(self):
        self.client.login(username='user', password='pass')
        url = reverse('delete_post', args=[self.post1.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)

    def test_delete_post_success_admin(self):
        self.client.login(username='staff', password='pass')
        url = reverse('delete_post', args=[self.post1.id])
        resp = self.client.post(url, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Post.objects.filter(id=self.post1.id).exists())
        msgs = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertIn("Post has been removed.", msgs)

    def test_delete_reply_success_admin(self):
        self.client.login(username='staff', password='pass')
        url = reverse('delete_reply', args=[self.reply1.id])
        resp = self.client.post(url, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Reply.objects.filter(id=self.reply1.id).exists())
        msgs = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertIn("Reply has been removed.", msgs)
