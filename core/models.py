from uuid import uuid4
import datetime

from django.db import models
from django.db.models.aggregates import Sum
from django.conf import settings


class PersonManager(models.Manager):
    def all_with_prefetch_movies(self):
        qs = self.get_queryset()
        return qs.prefetch_related(
            'directed', 'writing_credits', 'role_set__movie')


class Person(models.Model):
    first_name = models.CharField(max_length=140)
    last_name = models.CharField(max_length=140)
    born = models.DateField()
    died = models.DateField(null=True, blank=True)

    objects = PersonManager()

    class Meta:
        ordering = ('last_name', 'first_name')

    def __str__(self):
        if self.died:
            return '{}, {} ({}-{})'.format(
                self.last_name,
                self.first_name,
                datetime.date.strftime(self.born, '%d/%m/%Y'),
                datetime.date.strftime(self.died, '%d/%m/%Y'))
        return '{}, {} ({})'.format(
            self.last_name,
            self.first_name,
            datetime.date.strftime(self.born, '%d/%m/%Y'))


class MovieManager(models.Manager):
    def all_with_related_persons(self):
        qs = self.get_queryset()
        qs = qs.select_related('director')
        qs = qs.prefetch_related('writers', 'actors')
        return qs

    def all_with_related_persons_and_score(self):
        qs = self.all_with_related_persons()
        qs = qs.annotate(score=Sum('vote__value'))
        return qs


class Movie(models.Model):
    NOT_RATED = 0
    RATED_G = 1
    RATED_PG = 2
    RATED_PG13 = 3
    RATED_R = 4
    RATED_NC17 = 5
    RATINGS = (
        (NOT_RATED, 'NR - Not Rate'),
        (RATED_G, 'G - General Audiences'),
        (RATED_PG, 'PG – Parental Guidance Suggested'),
        (RATED_PG13, 'PG-13 – Parents Strongly Cautioned'),
        (RATED_R, 'R – Restricted'),
        (RATED_NC17, 'NC-17 – Adults Only'),
    )

    title = models.CharField(max_length=255)
    plot = models.TextField()
    year = models.PositiveIntegerField()
    rating = models.IntegerField(choices=RATINGS, default=NOT_RATED)
    runtime = models.PositiveIntegerField()
    website = models.URLField(blank=True)
    director = models.ForeignKey(
        to='Person',
        on_delete=models.SET_NULL,
        related_name='directed',
        null=True, blank=True)
    writers = models.ManyToManyField(
        to='Person', related_name='writing_credits', blank=True)
    actors = models.ManyToManyField(
        to='Person', through='role', related_name='acting_credits', blank=True)

    objects = MovieManager()

    class Meta:
        ordering = ('-year', 'title')

    def __str__(self):
        return '{} ({})'.format(self.title, self.year)


class Role(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.DO_NOTHING)
    person = models.ForeignKey(Person, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=140)

    class Meta:
        unique_together = ('movie', 'person', 'name')

    def __str__(self):
        return "{} {} {}".format(self.movie_id, self.person_id, self.name)


class VoteManager(models.Manager):
    def get_vote_or_unsaved_blank_vote(self, movie, user):
        try:
            return Vote.objects.get(movie=movie, user=user)
        except Vote.DoesNotExist:
            return Vote(movie=movie, user=user)


class Vote(models.Model):
    UP = 1
    DOWN = -1
    VALUE_CHOICES = (
        (UP, "👍"),
        (DOWN, "👎")
    )

    value = models.SmallIntegerField(choices=VALUE_CHOICES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    voted_on = models.DateTimeField(auto_now=True)

    objects = VoteManager()

    class Meta:
        unique_together = ('user', 'movie')


def movie_directory_path_with_uuid(instance, filename):
    return '{}/{}'.format(instance.movie_id, uuid4())


class MovieImage(models.Model):
    image = models.ImageField(upload_to=movie_directory_path_with_uuid)
    uploaded = models.DateTimeField(auto_now_add=True)
    movie = models.ForeignKey('Movie', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
