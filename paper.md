---
title: 'Scanbot: An STM Automation Bot'
tags:
  - Python
  - Scanning Tunneling Microscopy
  - STM
  - Automation
authors:
  - name: Julian Ceddia
    orcid: 0000-0003-3990-8852
    affiliation: "1, 2"
    corresponding: true
  - name: Jack Hellerstedt
    orcid: 0000-0003-2282-8223
    equal-contrib: false
    affiliation: "1, 2"
  - name: Benjamin Lowe
    orcid: 0000-0002-5157-7737
    equal-contrib: false
    affiliation: "1, 2"
  - name: Agustin Schiffrin
    orcid: 0000-0003-1140-8485
    equal-contrib: false
    affiliation: "1, 2"
affiliations:
 - name: School of Physics & Astronomy, Monash University, Clayton, Victoria 3800, Australia
   index: 1
 - name: ARC Centre of Excellence in Future Low-Energy Electronics Technologies, Monash University, Clayton, Victoria 3800, Australia
   index: 2
date: 13 March 2023
bibliography: paper.bib

---

# Summary

Scanning Tunnelling Microscopes (STM) are capable of capturing images of surfaces with atomic-scale resolution.
This is achieved by scanning an atomically sharp probe across the surface of the sample while monitoring an
electric current. However, the quality of STM data relies heavily on the atomic-scale geometry and composition
of the scanning probe apex, as well as the roughness and cleanliness of the scanned region. For instance, blunt tips
result in blurry images while contaminated tips can lead to noisy images due to interactions with the sample. 
As a result, optimal STM data acquisition commonly requires time-consuming tasks such as probe conditioning - i.e.
sharpening via "tip-shaping", where the apex of the probe can be refined by poking it into a clean metal surface - and
identification of areas of interest of the sample. Moreover, the quality of the probe can vary during a scan, especially 
when scanning over debris or excessively rough areas, necessitating additional tip-shaping.

Here, we present Scanbot, a program that fully automates common STM
data acquisition techniques, as well as tip-shaping and sample surveying.
Scanbot relies on a dual sample holder (DSH; figure 1), where a sample of interest is
mounted alongside a clean reference metal surface, which is ideal for tip preparation. 
Scanbot is able to analyse STM images and identify when the probe requires conditioning, subsequently moving it from the sample of interest to the 
clean reference metal, where it will prepare a scanning probe capable of obtaining high-quality STM images.
This is accomplished using built-in piezoceramic scanners to maneuver the STM tip while tracking its position through a camera
feed; figure 1b). Once Scanbot determines that the probe has been conditioned adequately, it moves the tip back to the sample of interest and STM data acquisition resumes.

![Tracking and maneuvering the STM probe above the dual sample holder (DSH).
**a)** Schematic of the STM tip over the dual sample holder setup.
A sample of interest is mounted next to a clean reference metal substrate (e.g. Au(111)) which is ideal for tip shaping.
**b)** Image from the camera feed used by Scanbot to track and maneuver the STM probe automatically from the sample to the clean reference metal,
where it can be refined. The red (green) marker indicates the probe apex position (target position, respectively).
See Scanbot [documentation](https://new-horizons-spm.github.io/scanbot/automation/) for a video example.
\label{fig:1}](TipTracking.png)

Figure 2 demonstrates Scanbot's ability to recondition a 'bad' tip on a clean reference metal surface. 
Scanbot can gently impinge the scanning probe apex onto a clean, flat region of the metal surface, which results in an imprint associated
with the geometry of the tip (figure 2a)). This imprint can then be scanned, and the resulting image is similar to
the auto-correlation function of the tip's apex. The quality of the tip can be assessed by measuring the area and circularity of the imprint.
If the imprint does not meet the desired criteria, a more aggressive tip shaping action is carried out, and the process is repeated until a high-quality tip is
achieved.

![Successive STM images (left to right) of the tip's imprint on a clean metal
surface, each following a more agressive tip-shaping action in a different location. The area
and circularity of each imprint reflects the geometry of the apex of the scanning probe. Thus
the process is repeated until a desired geometry is achieved.\label{fig:2}](AutoTipShaping.png)

# Statement of need

To reduce the time-intensive nature of STM experiments, various innovative solutions have been
implemented to automate specific tasks. For instance, Wang et al. created a Python package that
automates probe conditioning for Scanning Tunneling Spectroscopy [@Wang_2021]. However, this package
still requires manual preparation of the tip such that it can acquire clean images.
Some researchers have employed the use of machine learning algorithms to analyse
acquired images and determine when a probe needs refining [@Gordon_2020][@Rashidi_2018], then Reinforcement Learning (RL) agents can
condition the probe accordingly [@Schiffrin_2020]. Although these approaches have significantly advanced
automation in STM experiments, they are often tailored to specific surfaces and STM equipment, making it
challenging to transfer directly to other labs studying different systems or working with different
STM systems.

To overcome these limitations, we have developed Scanbot, a Python robot that is compatible with
a broader range of STMs, specifically those compatible with the Nanonis V5 software [@Nanonis_2015][@Ceddia_2022]. Additionally,
our package incorporates Scanbot's distinctive approach to tip shaping, which involves monitoring
the tip's motion above a dual sample holder. This method is particularly beneficial in experiments
where the sample's properties might make it challenging to achieve a high-quality scanning probe
without needing to manually switch out the sample for a clean metal on which the tip can be prepared.

Scanbot has been developed in a modular fashion, which means its functionality can easily be expanded
or improved through contributions from the open-source community. Furthermore, through the use of [hooks](https://new-horizons-spm.github.io/scanbot/hooks/),
users can customise or replace key funcionalities that are system- or lab-specific, without 
rewriting Scanbot's source code. This has the advantage of being able to update Scanbot to the latest version without
losing customised code. Such hooks can also be used to improve Scanbot's existing functionality or test potential new features. For instance,
Scanbot's algorithmic approach to automated tip shaping might benefit the integration of an RL agent. This could be achieved by
leveraging the hook [hk_tipShape](https://new-horizons-spm.github.io/scanbot/hooks/#hk_tipshape), where important parameters related to tip shaping can be adjusted based on images of the tip's imprint.
Complete documentation for Scanbot, including how such hooks can be leveraged, can be found at https://new-horizons-spm.github.io/scanbot.

# Acknowledgements

A.S. acknowledges funding support from the ARC Future
Fellowship scheme (FT150100426). J.C., B.L., and J.H.
acknowledge funding support from the Australian Research
Council (ARC) Centre of Excellence in Future Low-Energy
Electronics Technologies (CE170100039). J.C., and B.L. are supported
through an Australian Government Research Training Program
(RTP) Scholarship.

# References
