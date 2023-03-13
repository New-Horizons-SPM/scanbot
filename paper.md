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
    affiliation: 1
    corresponding: true
  - name: Jack Hellerstedt
    orcid: 0000-0003-2282-8223
    equal-contrib: false
    affiliation: 1
  - name: Benjamin Lowe
    orcid: 0000-0002-5157-7737
    equal-contrib: false
    affiliation: 1
  - name: Agustin Schiffrin
    orcid: 0000-0003-1140-8485
    equal-contrib: false
    affiliation: 1
affiliations:
 - name: Monash University, Australia
   index: 1
date: 13 March 2023
bibliography: paper.bib

---

# Summary

Scanning Tunnelling Microscopes (STM) are capable of capturing images of surfaces with atomic resolution.
This is achieved by scanning an atomically sharp probe across the surface of a sample while monitoring an
electric current. However, two common and time-consuming tasks in STM experiments are conditioning the
probe (such as sharpening it) and identifying areas of interest on a sample. The quality of STM images
heavily relies on the exact geometry and composition of the apex of the scanning probe. Blunt tips result
in blurry images while contaminated tips can lead to noisy images due to interactions with the sample. To
improve image quality, the probe can be conditioned using a process called "tip shaping," which involves
refining the tip by plunging it into a metallic substrate. Maintaining a "good tip" is not always
as scanning over debris or rough areas can alter the tip.

Fortunately, these tasks can be automated, and Scanbot is a program that not only automates several STM
data acquisition techniques but also fully automates tip shaping and sample surveying in STM experiments.
Scanbot utilises a dual sample holder (DSH) to prepare a high-quality tip, where a sample of interest can
be mounted alongside a clean metal surface, which is ideal for tip preparation. When the STM tip requires
refinement, Scanbot moves it from the sample of interest to the clean metal surface on the DSH. This is
accomplished using built-in motors to maneuver the STM tip while tracking its position through a camera
feed. After refining the tip, it is moved back to the sample of interest, where a survey can be conducted.
Figure 1 shows how the position of the STM tip is tracked while it is moved from a sample to a clean metal
surface for tip refinement.

![Tracking and maneuvering the STM probe above the dual sample holder.
The probe (inner blue box) is tracked within a moving window (outer blue box) as
the tip (red marker) is moved from its initial position to its target position
(green marker) over the clean metal surface.\label{fig:1}](TipTracking.png)

Figure 2 demonstrates Scanbot's ability to prepare a tip on a clean metal surface. By gently pushing the
apex of the scanning probe into an atomically flat region of a metal surface, an imprint is left that
reflects the geometry of the tip. This imprint can then be scanned, and the resulting image is similar to
the auto-correlation function of the tip's apex. The quality of the tip can be assessed by measuring the area,
symmetry, and center of mass of the imprint. If the imprint does not meet the desired criteria, a more
aggressive tip shaping action is carried out, and the process is repeated until a high-quality tip is
achieved.

![Successive images (left to right) of the tip's imprint on a clean metal
surface, each following a more agressive tip-shaping action in a different location. The Area
and circulatiry of each imprint reflects the geometry of the apex of the scanning probe. Thus
the process is repeated until a desired geometry is achieved.\label{fig:2}](AutoTipShaping.png)

# Statement of need

To reduce the time-intensive nature of STM experiments, various innovative solutions have been
implemented to automate specific tasks. For instance, Wang et al. created a Python package that
automates probe conditioning for Scanning Tunneling Spectroscopy [@Wang_2021]. However, this package
still requires manual preparation of the tip for STM such that it can produce clean images.
Some researchers have employed the use of machine learning algorithms [@Gordon_2020] to analyse
acquired images and determine when a probe needs refining, then Reinforcement Learning agents can
condition the probe accordingly [@Schiffrin_2020]. Although these approaches have significantly advanced
automated STM experiments, they are often tailored to specific surfaces and STM equipment, making it
challenging to transfer the code to other labs studying different systems or working with different
brands of STMs.

To overcome these limitations, we have developed Scanbot, a Python robot that is compatible with
a broader range of STMs, specifically those compatible with the Nanonis V5 software [@Ceddia_2022]. Additionally,
our package incorporates Scanbot's distinctive approach to tip shaping, which involves monitoring
the tip's motion above a dual sample holder. This method is particularly beneficial in experiments
where the sample's properties might make it challenging to achieve a high-quality scanning probe
without needing to manually switch out the sample for a clean metal on which the tip can be prepared.

Scanbot has been developed in a modular fashion, which means its functionality can easily be expanded
or improved through contributions from the open-source community. For instance, the algorithmic
approach to tip shaping might benefit from adaption to machine learning. This could be achieved by
leveraging hooks in the code where alternative, custom Python scripts can seamlessly replace existing
functionality, with the only requirement being that the inputs and outputs are the same. Complete
documentation for Scanbot, including how such hooks can be leveraged, can be found
[here](https://new-horizons-spm.github.io/scanbot/). With Scanbot, researchers can spend less time
preparing probes and more time acquiring high-quality STM data.

# Acknowledgements

We acknowledge contributions from FLEET for funding this project through their research translation program

# References
