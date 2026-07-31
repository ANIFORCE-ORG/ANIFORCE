# ANIFORCE

ANIFORCE manages advertising media independently from the external platform accounts where that media exists.

## Material Library

**Material**:
A media file managed by ANIFORCE, independent of any advertising platform identity.
_Avoid_: Creative, ad creative, platform asset

**Platform Asset**:
A platform-specific identity for a Material in one Advertising Account, such as a Meta AdImage or AdVideo.
_Avoid_: Material, creative

**Material Sync Run**:
One attempt to import selected asset types from one Advertising Account into the Material library.
_Avoid_: Campaign sync, Business Portfolio sync

## Platform Access

**Platform Connection**:
An authorization granted by an external platform identity, containing the credentials used to access platform resources.
_Avoid_: Advertising Account

**Advertising Account**:
An external account that owns or exposes advertising assets and delivery objects. Material import is scoped to one Advertising Account.
_Avoid_: Platform Connection, Business Portfolio

**Business Portfolio**:
A Meta organizational and authorization container that can expose multiple Advertising Accounts; it is not a Material import boundary.
_Avoid_: Advertising Account, BM account
