from sys import path

from django.conf.urls import url

from apps.feature_toggles.ops_features import is_reviews_enabled
from apps.reviews import views

app_name = 'reviews'

urlpatterns = [
    url(r'^$', views.ReviewListView.as_view(), name='list'),
    url(r'^create$', views.CreateReviewView.as_view(), name='create'),
    url(r'^my$', views.PatientReviewListView.as_view(), name='my_list'),
    url(r'^my/<int:pk>$', views.SinglePatientReviewView.as_view(), name='my_item'),
    # url(
    #     r'^reviews/(?P<review_id>\d+)/replies/$',
    #     views.ReviewRepliesView.as_view({'post': 'create'}),
    #     name='reviews_replies',
    # ),
    # url(
    #     r'^reviews/reply/(?P<reply_id>\d+)$',
    #     views.ReviewRepliesView.as_view({'put': 'update', 'delete': 'destroy'}),
    #     name='one_review_reply',
    # ),
    # url(
    #     r'^reviews/info$', views.ReviewListView.as_view(), {'info': True}, name='reviews_list_info'
    # ),
    # url(
    #     r'^reviews/(?P<contractor_id>\d+)$',
    #     views.ReviewListView.as_view(),
    #     name='reviews_list_contractor',
    # ),
    # url(
    #     r'^reviews/(?P<contractor_id>\d+)/info$',
    #     views.ReviewListView.as_view(),
    #     {'info': True},
    #     name='reviews_list_contractor_info',
    # ),
]

if not is_reviews_enabled.is_enabled:
    urlpatterns = []
