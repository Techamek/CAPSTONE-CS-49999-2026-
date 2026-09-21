/**
 * Live price estimate for the public submission form. Mirrors
 * calculate_price() in app.py — the server always recalculates
 * authoritatively on submit, this is just a live preview for the guest.
 */
(function (global) {
  'use strict';

  function computeEstimate(config, input) {
    var guestCount = Math.max(0, parseInt(input.guestCount, 10) || 0);
    var durationHours = Math.max(0, parseFloat(input.durationHours) || 0);
    var enhancementKeys = input.enhancementKeys || [];

    var spaceRentalCost = config.spaceRentalPerHour * durationHours;
    if (guestCount > config.includedGuestCap) {
      spaceRentalCost += config.overageSurchargePerHour * durationHours;
    }

    var menuCost = config.menuPricePerPerson * guestCount;

    var enhancementsCost = 0;
    var enhancementLines = [];
    enhancementKeys.forEach(function (key) {
      var spec = config.enhancements[key];
      if (!spec) return;
      var lineTotal = (spec.flat || 0) + (spec.per_hour || 0) * durationHours + (spec.per_person || 0) * guestCount;
      enhancementsCost += lineTotal;
      enhancementLines.push({ key: key, label: spec.label, total: lineTotal });
    });

    var total = spaceRentalCost + menuCost + enhancementsCost;

    return {
      spaceRentalCost: spaceRentalCost,
      menuCost: menuCost,
      enhancementsCost: enhancementsCost,
      enhancementLines: enhancementLines,
      total: total,
      depositDue: spaceRentalCost,
      overGuestCap: guestCount > config.maxGuestCapacity,
      overIncludedCap: guestCount > config.includedGuestCap,
    };
  }

  function money(n) {
    return '$' + (Math.round(n * 100) / 100).toFixed(2);
  }

  global.PriceEstimator = { computeEstimate: computeEstimate, money: money };
})(window);
