# -*- coding: utf8 -*-
from __future__ import unicode_literals
import json
import re
from django.core.management.base import BaseCommand, CommandError
from awards.models import Award, YearAward, Nomination, Vote
from serebii.models import Fic, Member, FicPage, MemberPage


def compare_spaceless(value1, value2):
    return re.sub(r'\s', '', value1) == re.sub(r'\s', '', value2)


class Command(BaseCommand):
    help = "Loads nominations into the database from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument('file', type=open)
        parser.add_argument('--year', type=int)
        parser.add_argument('--dry-run', action='store_true', dest='dry_run', default=False)

    def handle(self, file, *args, **options):
        try:
            data = json.load(file)
        except (IOError, ValueError):
            raise CommandError("Invalid JSON file!")
        dry_run = options['dry_run']
        print dry_run
        for year, nominations in data.items():
            if options['year'] and int(year) != options['year']:
                continue
            print "Nominations for year {}!".format(year)

            placeholder_nominations = set(Nomination.objects.from_year(year).filter(member_id=388))
            for nomination in nominations:
                try:
                    award = Award.objects.get(name=nomination['award'])
                except Award.DoesNotExist:
                    print "No such award as '{}'!".format(nomination['award'])
                    continue
                try:
                    year_award = YearAward.objects.get(award=award, year=year)
                except YearAward.DoesNotExist:
                    print "The award '{}' was not active in the year {}!".format(nomination['award'], year)
                    continue
                nomination_params = {
                    'verified': True,
                    'award': award,
                    'year': year
                }
                if nomination.get('nominee_thread_link'):
                    fic = FicPage.from_url(nomination.get('nominee_thread_link'), save=True).object
                    nomination_params['fic'] = fic
                elif nomination.get('nominee_user_link'):
                    nominee = MemberPage.from_url(nomination.get('nominee_user_link'), save=True).object
                    nomination_params['nominee'] = nominee
                else:
                    print "This nomination has neither a thread nor a user link!", nomination
                    continue
                existing_nominations = Nomination.objects.filter(**nomination_params)
                existing_noms = [nom for nom in existing_nominations if not award.has_detail or compare_spaceless(nom.detail, nomination.get('detail', ''))]
                if existing_noms:
                    member = MemberPage.from_params(user_id=nomination['nominator_user_id'], save=True).object
                    for nom in existing_noms:
                        if nom.member == member:
                            # We've already added this nomination by this person - just make sure we have the comment right
                            nom.comment = nomination.get('comment', '')
                            nom.save()
                            if nom in placeholder_nominations:
                                placeholder_nominations.remove(nom)
                            break
                        if nom.member_id == 388 and nom in placeholder_nominations:
                            # This is a placeholder nomination
                            if not dry_run:
                                nom.member = member
                                nom.comment = nomination.get('comment', '')
                                nom.save()
                            placeholder_nominations.remove(nom)
                            break
                    else:
                        # No placeholder nomination left - create a new one!
                        if not dry_run:
                            Nomination.objects.create(
                                detail=nomination.get('detail', ''),
                                member=member,
                                comment=nomination.get('comment', ''),
                                **nomination_params
                            )
                else:
                    print "No nominations exist matching these filters!", nomination_params, nomination['detail'].encode('cp437', 'ignore') if 'detail' in nomination else None, existing_nominations

            print "Unmatched placeholders:", placeholder_nominations
