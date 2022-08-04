# -*- coding: utf8 -*-
import re
from django.core.management.base import BaseCommand, CommandError
from awards.models import Award, YearAward, Nomination, Vote
from forum.models import Fic, Member, FicPage, MemberPage
from old_data import awards, year_awards, fics, nomination_links, nominations, voters, votes


def convert_formatting(text):
    substitutions = {
        r'<(/?)(i|em)>': '[\\1i]',
        r'<(/?)(b|strong)>': '[\\1b]',
        r'\s*<br( /)?>': '\r\n',
        r'&lt;': '<',
        r'&gt;': '>'
    }
    for pattern, replacement in substitutions.items():
        text = re.sub(pattern, replacement, text)
    return text


def compare_spaceless(value1, value2):
    return re.sub(r'\s', '', value1) == re.sub(r'\s', '', value2)


class Command(BaseCommand):
    help = "Loads old awards data into the database."

    def handle(self, *args, **options):
        awards_map = {}

        for id, name, topcat, nomdetails, displayorder in awards:
            award, new = Award.objects.get_or_create(name=name, defaults={
                'category_id': topcat,
                'description': '',
                'has_person': nomdetails in (0, 3),
                'has_fic': nomdetails in (1, 2),
                'has_detail': nomdetails == 2,
                'has_samples': nomdetails == 3,
                'requires_new': False,
                'detail_character_limit': None,
                'display_order': displayorder
            })
            awards_map[id] = award
            if new:
                print("- Created new award:", award)

        for cat, year, active in year_awards:
            if active:
                year_award, new = YearAward.objects.get_or_create(award=awards_map[cat], year=year)
                if new:
                    print("Created new YearAward:", year_award)

        fic_map = {}
        username_map = {}

        for id, title, threadid, postid, author_username in fics:
            fic = FicPage.from_params(thread_id=threadid, post_id=postid, save=True).object
            fic_map[id] = fic
            username_map[author_username] = fic.get_authors()[0]

        link_map = {}

        for id, nomid, link in nomination_links:
            if nomid not in link_map:
                link_map[nomid] = []
            link_map[nomid].append(link)

        nomination_map = {}

        for id, catid, fic, author, threadid, details, year, ficid in nominations:
            award = awards_map[catid]
            params = {
                'award': award,
                'year': year
            }
            if award.has_person:
                if author in username_map:
                    # We've already found out who this username is! Use that member
                    params['nominee'] = username_map[author]
                else:
                    # Get or create a member with the given username
                    params['nominee'], new = Member.objects.get_or_create(username=author)
                    if new:
                        print("Created new member:", params['nominee'])
            if award.has_fic:
                params['fic'] = fic_map[ficid]
            if award.has_detail:
                details = convert_formatting(details)
            for link in link_map.get(id, [None]):
                if award.has_samples:
                    params['link'] = link
                existing_nominations = Nomination.objects.filter(**params)
                if existing_nominations:
                    if not award.has_detail:
                        # This is definitely a matching nomination - just use the first one.
                        nomination = existing_nominations[0]
                    else:
                        # Let's do some work to figure out if the details match.
                        for nom in existing_nominations:
                            if compare_spaceless(nom.detail, details):
                                nomination = nom
                                break
                        else:
                            nomination = None
                else:
                    nomination = None
                if not nomination:
                    nomination = Nomination.objects.create(member=Member.objects.get(user_id=388), verified=True, detail=details or '', **params)
                    print("Created new nomination", nomination)
                nomination_map[id] = nomination

        voter_map = {}

        for username, approved, year in voters:
            if year not in voter_map:
                voter_map[year] = {}
            voter_map[year][username] = bool(approved)

        for username, vote, cat, year in votes:
            if voter_map[year][username] and vote in nomination_map:
                if username in username_map:
                    member = username_map[username]
                else:
                    member, new = Member.objects.get_or_create(username=username)
                    if new:
                        print("Created new member:", member)
                v, new = Vote.objects.get_or_create(year=year, member=member, award=awards_map[cat], defaults={'nomination': nomination_map[vote], 'verified': True})
                if new:
                    print("Created vote:", v)
