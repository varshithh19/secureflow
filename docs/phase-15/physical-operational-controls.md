# Phase 15 - Physical & Operational Security Controls

This document details physical, edge, and operational security procedures for traffic controllers and road sensors.

---

## 1. Physical Enclosure Security
- Traffic signal controller cabinets must be locked with tamper-evident physical seals and monitored by door-intrusion microswitches.
- Physical cabinet tamper signals trigger immediate high-priority alerts to the central operations center.

## 2. Hardware Security Modules (HSM) & Secure Elements
- Edge sensors and physical controllers store HMAC pre-shared keys inside tamper-resistant hardware crypto chips (TPM 2.0 or ATECC608B).
- Private keys cannot be extracted via physical bus probing or memory dumping.

## 3. Fail-Safe Hardware Fallback (NFR-02)
- If network connection to the central backend is severed for $> 30$ minutes, local controllers revert autonomously to pre-programmed fixed-time safety cycles.
- Hardware conflict monitor units (CMU) physically prevent conflicting green signals on intersecting road axes.
