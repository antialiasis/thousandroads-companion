# Review blitz App

This app is intended to assist in running review events such as Thousand Roads' annual "Review Blitz." Participants can submit reviews for fanfics, which users with appropriate permissions can approve or reject depending on whether they meet the event's requirements, and the system will keep track of how many points each participant has earned over the course of the event.

# Blitz-Specific Admin Controls

These admin views are used by the reviewblitz app:

- **Blitz reviews**: Infortmation for reviews that have, specifically, been submitted as part of one or more events. Notably, if you need to manually approve a review, it can be done through this admin view.
- **Review blitz scorings**: Settings that define the scoring scheme for a particular review event, e.g. by defining the point values for each chapter reviewed, how much a theme bonus is worth, etc. You'll want to create a new one of these if the scoring system your event will use differs from those utilized by past review events.
- **Review blitzes**: Reviewing events themselves. If you want to kick off a new event, you'll want to start by defining the variables here. The event will automatically be active between the start and end dates that you define, allowing participants to submit reviews to it.
- **Reviews**: Reviews submitted to the system, whether or not they're considered part of an event. It is generally going to be easier to add a review through the review submission interface than through the admin.
