********************************************
3 scrapy spiders implemented with ItemLoader
********************************************


There are 3 spiders implemented with ItemLoader and without it.
You can consider usage of ItemLoader for your spiders
after reading the readme file until the end.

**Table of Contents**

.. contents::
    :local:
    :depth: 1
    :backlinks: none

============
Introduction
============

If you are a newbie in scrapy but have already written several
spiders and gonna write more spiders, you should
consider usage of ItemLoader if you don't use it yet.
I will not describe features of ItemLoader and processors,
check out `official docs <http://doc.scrapy.org/en/latest/topics/loaders.html>`_ for this. But I will show migration
from real world spiders without ItemLoader to spiders with ItemLoaders.


===============
Migration steps
===============

1. `Replace bare item field assignments with ItemLoader <https://github.com/taroved/3spiders-with-itemloader/commit/1bcdd9db2e89c1f8be7b9ed1f24c11cca76fe5f0>`_
2. `Usage of context selectors which simplify code <https://github.com/taroved/3spiders-with-itemloader/commit/9f8b3854b0a329bb2cf6a317caa73e12bed8dc5e>`_
3. `Required step: add output processors <https://github.com/taroved/3spiders-with-itemloader/commit/93fe96a08a9ee829248165f005b2e1f75c10d8c0>`_
4. `Default output processor <https://github.com/taroved/3spiders-with-itemloader/commit/238f3af35b89c93690efc9c2aa57162f26f13f34>`_
5. `Optional step: extending ItemLoader <https://github.com/taroved/3spiders-with-itemloader/commit/ffd0e3605cf4e1d4d187333337b1746f01e38397#diff-0>`_


============
Installation
============

.. code-block:: bash

    $ pip install scrapy
    $ git clone git@github.com:taroved/3spiders-with-itemloader.git
    # check contracts for spiders
    $ cd 3spiders-with-itemloader
    $ scrapy check

========
Scraping
========

.. code-block:: bash

    $ scrapy crawl apple

Output scrapped data to the file and write log file:

.. code-block:: bash

    $ scrapy crawl apple -o apple.json --logfile=apple.log

============
More spiders
============

The second spider scrape locations from wetseal.com:

.. code-block:: bash

    $ scrapy crawl wetseal -o wetseal.json


The third spider scrape products from hhgregg.com:

.. code-block:: bash

    $ scrapy crawl hhgregg -o hhgregg.json


=======
Summary
=======

I haven't said a lot, but you can take a look at the full `diff <https://github.com/taroved/3spiders-with-itemloader/compare/without...with>`_
between versions without and with ItemLoader for the spiders and make the right decision.


=======
License
=======

WTFPL

