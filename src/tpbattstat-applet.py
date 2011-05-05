#!/usr/bin/env python
##########################################################################
# TPBattStatApplet v0.1
# Copyright 2011 Elliot Wolk
##########################################################################
# This file is part of TPBattStatApplet.
#
# TPBattStatApplet is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# TPBattStatApplet is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with TPBattStatApplet. If not, see <http://www.gnu.org/licenses/>.
##########################################################################

import pygtk
pygtk.require('2.0')

import sys
from subprocess import Popen, PIPE
import gtk, gtk.gdk, gobject
import gnomeapplet

SMAPI_BATTACCESS = '/usr/bin/smapi-battaccess'

def enum(*sequential, **named):
  enums = dict(zip(sequential, range(len(sequential))), **named)
  return type('Enum', (), enums)

State = enum('CHARGING', 'DISCHARGING', 'IDLE')
DischargeStrategy = enum('SYSTEM', 'LEAPFROG', 'CHASING')
ChargeStrategy = enum('SYSTEM', 'LEAPFROG', 'CHASING', 'BRACKETS')

class BattStatus():
  def __init__(self):
    self.ac_connected = smapi_get(-1, 'ac_connected')
    self.batt0 = BattInfo(0)
    self.batt1 = BattInfo(1)
  def ensure_charging(self, batt_id)
    previnhib0 = self.batt0.inhibit_charge_minutes
    previnhib1 = self.batt1.inhibit_charge_minutes
    charge0 = self.batt0.state == State.CHARGING
    charge1 = self.batt1.state == State.CHARGING
    if batt_id == 0 and (previnhib0 or (!charge0 and !previnhib1)):
      smapi_set(0, 'inhibit_charge_minutes', '0')
      smapi_set(1, 'inhibit_charge_minutes', '1')
    elif batt_id == 1 and (previnhib1 or (!charge1 and !previnhib0)):
      smapi_set(1, 'inhibit_charge_minutes', '0')
      smapi_set(0, 'inhibit_charge_minutes', '1')
  def perhaps_inhibit_charge(self, strat, leapfrogThreshold, \
    brackets, bracketsPrefBattId):
    never_inhibit = !self.ac_connected or \
      !self.batt0.installed or !self.batt1.installed or \
      start == ChargeStrategy.SYSTEM
    charge0 = self.batt0.state == State.CHARGING
    charge1 = self.batt1.state == State.CHARGING
    per0 = self.batt0.remaining_percent
    per1 = self.batt1.remaining_percent
    if never_inhibit:
      if self.batt0.inhibit_charge_minutes:
        smapi_set(0, 'inhibit_charge_minutes', '0')
      if self.batt1.inhibit_charge_minutes:
        smapi_set(1, 'inhibit_charge_minutes', '0')
    elif strat == ChargeStrategy.LEAPFROG:
      if per1 - per0 > leapfrogThreshold:
        ensure_charging(1)
      elif per0 - per1 > leapfrogThreshold:
        ensure_charging(0)
    elif strat == ChargeStrategy.CHASING:
      if per1 > per0:
        ensure_charging(0)
      elif per0 > per1:
        ensure_charging(1)
    elif strat == ChargeStrategy.BRACKETS:
      prefBat = bracketsPrefBattId
      unprefBat = 1 - prefBat
      percentPref = prefBat == 0 ? per0 : per1
      percentUnpref = unprefBat == 0 ? per0 : per1
      for bracket in brackets:
        if percentPref < bracket:
          ensure_charging(prefBat)
          break
        elif percentUnpref < bracket:
          ensure_charging(unprefBat)
          break

  def perhaps_force_discharge(self, strat, leapfrogThreshold):
    should_force = ac_connected and batt0.installed and batt1.installed
    dis0 = self.batt0.state == State.DISCHARGING
    dis1 = self.batt1.state == State.DISCHARGING
    per0 = self.batt0.remaining_percent
    per1 = self.batt1.remaining_percent
    force0 = 0
    force1 = 1
    if should_force and strat == DischargeStrategy.LEAPFROG:
      if dis0:
        if per1 - per0 > leapfrogThreshold:
          force1 = 1
        elif per0 > leapfrogThreshold:
          force0 = 1
      elif dis1:
        if per0 - per1 > leapfrogThreshold:
          force0 = 1
        elif per1 > leapfrogThreshold:
          force1 = 1
      elif per0 > leapfrogThreshold and per0 > per1:
        force0 = 1
      elif per1 > leapfrogThreshold and per1 > per0:
        force1 = 1
    elif should_force and strat == DischargeStrategy.CHASING:
      if per0 > per1:
        force0 = 1
      elif per1 > per0:
        force1 = 1

    prevforce0 = self.batt0.force_discharge
    prevforce1 = self.batt1.force_discharge

    if prevforce0 != force0 or prevforce1 != force1:
      smapi_set(0, 'force_discharge', str(force0))
      smapi_set(1, 'force_discharge', str(force1))


class BattInfo():
  def __init__(self, batt_id):
    self.batt_id = batt_id
    self.installed = smapi_get(batt_id, 'installed')
    self.force_discharge = smapi_get(batt_id, 'force_discharge')
    self.inhibit_charge_minutes = smapi_get(batt_id, 'inhibit_charge_minutes')
    self.remaining_percent = smapi_get(batt_id, 'remaining_percent')
    self.power_avg = smapi_get(batt_id, 'power_avg')
    self.remaining_capacity = smapi_get(batt_id, 'remaining_capacity')
    self.last_full_capacity = smapi_get(batt_id, 'last_full_capacity')
    self.design_capacity = smapi_get(batt_id, 'design_capacity')
    state = smapi_get(batt_id, 'state')
    if state == 'charging':
      self.state = State.CHARGING
    elif state == 'discharging':
      self.state = State.DISCHARGING
    elif state == 'idle':
      self.state = State.IDLE
    else
      self.state = None

def smapi_get(batt_id, prop):
  try:
    p = Popen([SMAPI_BATTACCESS, '-g', str(batt_id), prop], stdout=PIPE)
    (stdout, _) = p.communicate()
    return stdout
  except:
    msg = 'Could not get ' + prop + ' on bat ' + str(batt_id)
    print >> sys.stderr, msg
    return -1

def smapi_set(batt_id, prop, val):
  try:
    p = Popen([SMAPI_BATTACCESS, '-s', str(batt_id), prop, val])
    p.wait()
  except:
    msg = 'Could not set ' + prop + '=' + val + ' on bat ' + str(batt_id)
    print >> sys.stderr, msg

#def main():
#  BattStatus().perhaps_force_discharge(DischargeStrategy.LEAPFROG, 3)
#if __name__ == "__main__":
#  sys.exit(main())

class TPBattStatApplet():
    def __init__(self, applet):
        self.applet=applet
        self.label = gtk.Label("")
        self.applet.add(self.label)
        self.applet.set_background_widget(self.applet)
        gobject.timeout_add_seconds(15, self.update)
        self.update()
        self.applet.show_all()
        
    def update(self):
        self.label.set_text(contents_func())
        return True

def factory(applet, iid):
    TPBattStatApplet(applet)
    return True

if len(sys.argv) == 2 and sys.argv[1] == "run-in-window":  
  print "running in window"
  main_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
  main_window.set_title("TPBattStatApplet")
  main_window.connect("destroy", gtk.main_quit) 
  app = gnomeapplet.Applet()
  factory(app, None)
  app.reparent(main_window)
  main_window.show_all()
  gtk.main()
  sys.exit()

gnomeapplet.bonobo_factory("OAFIID:TPBattStatApplet_Factory", 
                                gnomeapplet.Applet.__gtype__, 
                                "ThinkPad Battery Status Applet",
                                "0",
                                factory)
