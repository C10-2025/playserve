
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib import messages

from community.models import Community, Post, Reply

URL_DISCOVER        = 'discover_communities'
URL_MY              = 'my_communities'
URL_JOIN            = 'join_community'
URL_DETAIL          = 'community_detail'
URL_CREATE_COMM     = 'create_community'
URL_UPDATE_COMM     = 'update_community'
URL_DELETE_COMM     = 'delete_community'
URL_CREATE_POST     = 'create_post'
URL_CREATE_REPLY    = 'create_reply'
URL_DELETE_POST     = 'delete_post'
URL_DELETE_REPLY    = 'delete_reply'


class CommunityViewsTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Users
        self.admin = User.objects.create_user('admin', password='pass', is_staff=True)
        self.creator = User.objects.create_user('creator', password='pass', is_staff=True)
        self.member  = User.objects.create_user('member',  password='pass')
        self.stranger= User.objects.create_user('stranger',password='pass')

        # Community (creator = self.creator)
        self.comm = Community.objects.create(
            name='Tennis Lovers',
            description='All about tennis',
            creator=self.creator
        )
        # creator belum otomatis member -> behavior di view: auto-add saat open detail
        # tambahkan 1 member biasa
        self.comm.members.add(self.member)

        # Sample Post & Reply
        self.post = Post.objects.create(
            community=self.comm,
            title='Best rackets 2025',
            author=self.member,
            content='Yonex vs Babolat'
        )
        self.reply = Reply.objects.create(
            post=self.post,
            author=self.member,
            content='I vote Yonex.'
        )

    # ---------------- Discover & Search ----------------
    def test_discover_requires_login(self):
        resp = self.client.get(reverse(URL_DISCOVER))
        # redirect to login
        self.assertEqual(resp.status_code, 302)

    def test_discover_list_and_search(self):
        self.client.login(username='member', password='pass')

        # list all
        resp = self.client.get(reverse(URL_DISCOVER))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Tennis Lovers')

        # search (ic contains)
        resp = self.client.get(reverse(URL_DISCOVER), {'q': 'tennis'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Tennis Lovers')

        resp = self.client.get(reverse(URL_DISCOVER), {'q': 'basket'})
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'Tennis Lovers')

    # ---------------- My Communities Tabs ----------------


    def test_my_communities_created_tab(self):
        self.client.login(username='creator', password='pass')
        resp = self.client.get(reverse(URL_MY), {'tab': 'created'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Created by Me')
        self.assertContains(resp, 'Tennis Lovers')

    # ---------------- Join Community (JSON) ----------------
    def test_join_community_via_post(self):
        self.client.login(username='stranger', password='pass')
        url = reverse(URL_JOIN, args=[self.comm.id])

        # method selain POST -> 405
        resp_get = self.client.get(url)
        self.assertEqual(resp_get.status_code, 405)

        # join pertama kali
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'joined')
        self.assertTrue(self.comm.members.filter(id=self.stranger.id).exists())

        # join lagi -> already_joined
        resp2 = self.client.post(url)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()['status'], 'already_joined')

    # ---------------- Community Detail & Auto-add Creator ----------------
    def test_detail_requires_membership_or_auto_add_creator(self):
        # creator bukan member awalnya -> auto-add ketika buka detail
        self.client.login(username='creator', password='pass')
        url = reverse(URL_DETAIL, args=[self.comm.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(self.comm.members.filter(id=self.creator.id).exists())

        # stranger belum member -> redirect & message error
        self.client.logout()
        self.client.login(username='stranger', password='pass')
        resp2 = self.client.get(url, follow=True)
        # redirected ke discover
        self.assertEqual(resp2.status_code, 200)
        # pastikan message error dikirim
        msgs = list(messages.get_messages(resp2.wsgi_request))
        self.assertTrue(any("must join this community" in str(m) for m in msgs))

    # ---------------- Create / Update / Delete Community (admin+creator) ----------------
    def test_create_community_admin_only(self):
        # non-admin login -> redirect ke login (user_passes_test)
        self.client.login(username='member', password='pass')
        resp = self.client.post(reverse(URL_CREATE_COMM), {'name':'X','description':'Y'})
        self.assertEqual(resp.status_code, 302)

        # admin boleh membuat
        self.client.logout()
        self.client.login(username='admin', password='pass')
        resp2 = self.client.post(reverse(URL_CREATE_COMM), {'name':'Pickleball','description':'fun'})
        self.assertEqual(resp2.status_code, 302)
        self.assertTrue(Community.objects.filter(name='Pickleball').exists())
        # admin auto-join komunitas yang dia buat
        newc = Community.objects.get(name='Pickleball')
        self.assertTrue(newc.members.filter(id=self.admin.id).exists())

    def test_update_community_only_creator_admin(self):
        # admin tapi BUKAN creator -> ditolak oleh check creator
        self.client.login(username='admin', password='pass')
        resp = self.client.post(reverse(URL_UPDATE_COMM, args=[self.comm.id]),
                                {'name':'NewName','description':'Desc'})
        self.assertEqual(resp.status_code, 302)
        self.comm.refresh_from_db()
        self.assertEqual(self.comm.name, 'Tennis Lovers')  # tidak berubah

        # creator (juga admin? di setup creator is_staff=True) -> boleh update
        # kalau creator bukan admin di app kamu, set is_staff=True; view butuh keduanya
        self.client.logout()
        self.creator.is_staff = True
        self.creator.save()
        self.client.login(username='creator', password='pass')
        resp2 = self.client.post(reverse(URL_UPDATE_COMM, args=[self.comm.id]),
                                 {'name':'Renamed','description':'Updated'})
        self.assertEqual(resp2.status_code, 302)
        self.comm.refresh_from_db()
        self.assertEqual(self.comm.name, 'Renamed')

    def test_delete_community_only_creator_admin(self):
        # admin tapi bukan creator -> ditolak
        self.client.login(username='admin', password='pass')
        resp = self.client.post(reverse(URL_DELETE_COMM, args=[self.comm.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Community.objects.filter(id=self.comm.id).exists())

        # creator+admin -> boleh hapus
        self.client.logout()
        self.creator.is_staff = True
        self.creator.save()
        self.client.login(username='creator', password='pass')
        resp2 = self.client.post(reverse(URL_DELETE_COMM, args=[self.comm.id]))
        self.assertEqual(resp2.status_code, 302)
        self.assertFalse(Community.objects.filter(id=self.comm.id).exists())

    # ---------------- Post & Reply ----------------
    def test_create_post_requires_membership_and_fields(self):
        self.client.login(username='stranger', password='pass')
        url = reverse(URL_CREATE_POST, args=[self.comm.id])

        # bukan member -> redirect ke discover
        resp = self.client.post(url, {'title':'T','content':'C'})
        self.assertEqual(resp.status_code, 302)

        # jadi member dulu
        self.comm.members.add(self.stranger)

        # invalid (missing fields)
        resp2 = self.client.post(url, {'title':'', 'content':''}, follow=True)
        self.assertEqual(resp2.status_code, 200)
        # tetap redirect ke detail; tidak membuat post baru
        self.assertEqual(Post.objects.filter(community=self.comm).count(), 1)  # hanya self.post

        # valid
        resp3 = self.client.post(url, {'title':'Hello','content':'World'})
        self.assertEqual(resp3.status_code, 302)
        self.assertEqual(Post.objects.filter(community=self.comm).count(), 2)

    def test_create_reply_requires_membership(self):
        self.client.login(username='stranger', password='pass')
        url = reverse(URL_CREATE_REPLY, args=[self.post.id])

        # bukan member -> redirect discover
        resp = self.client.post(url, {'content':'Hi'})
        self.assertEqual(resp.status_code, 302)

        # jadi member → sukses
        self.comm.members.add(self.stranger)
        resp2 = self.client.post(url, {'content':'Hi'})
        self.assertEqual(resp2.status_code, 302)
        self.assertTrue(Reply.objects.filter(post=self.post, author=self.stranger, content='Hi').exists())

    def test_delete_post_reply_admin_only(self):
        # non-admin -> redirect
        self.client.login(username='member', password='pass')
        resp1 = self.client.post(reverse(URL_DELETE_POST, args=[self.post.id]))
        self.assertEqual(resp1.status_code, 302)
        self.assertTrue(Post.objects.filter(id=self.post.id).exists())

        resp2 = self.client.post(reverse(URL_DELETE_REPLY, args=[self.reply.id]))
        self.assertEqual(resp2.status_code, 302)
        self.assertTrue(Reply.objects.filter(id=self.reply.id).exists())

        # admin -> boleh hapus
        self.client.logout()
        self.client.login(username='admin', password='pass')
        resp3 = self.client.post(reverse(URL_DELETE_POST, args=[self.post.id]))
        self.assertEqual(resp3.status_code, 302)
        self.assertFalse(Post.objects.filter(id=self.post.id).exists())

        # buat reply baru dahulu untuk dihapus
        p = Post.objects.create(community=self.comm, title='Temp', author=self.member, content='x')
        r = Reply.objects.create(post=p, author=self.member, content='y')
        resp4 = self.client.post(reverse(URL_DELETE_REPLY, args=[r.id]))
        self.assertEqual(resp4.status_code, 302)
        self.assertFalse(Reply.objects.filter(id=r.id).exists())


class CommunityModelsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u', password='p')
        self.c = Community.objects.create(name='X', description='Y', creator=self.user)

    def test_str_methods(self):
        p1 = Post.objects.create(community=self.c, author=self.user, title='A', content='a')
        p2 = Post.objects.create(community=self.c, author=self.user, title='B', content='b')
        r1 = Reply.objects.create(post=p2, author=self.user, content='c')
        r2 = Reply.objects.create(post=p2, author=self.user, content='d')

        # __str__
        self.assertEqual(str(self.c), 'X')
        self.assertIn('Post by', str(p1))
        self.assertIn('Reply by', str(r1))

        # ordering: Post desc, Reply asc
        posts = list(Post.objects.filter(community=self.c))
        replies = list(Reply.objects.filter(post=p2))
        self.assertEqual(posts[0].id, p2.id)   # p2 newer first
        self.assertEqual(replies[0].id, r1.id) # r1 earlier first
