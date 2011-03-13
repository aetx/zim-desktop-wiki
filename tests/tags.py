# -*- coding: utf-8 -*-

# Copyright 2011 Jaap Karssenberg <jaap.karssenberg@gmail.com>

import tests

import gtk
import pango

from zim.index import Index, IndexPath, IndexTag
from zim.notebook import Path
from zim.gui.pageindex import FGCOLOR_COL, \
	EMPTY_COL, NAME_COL, PATH_COL, STYLE_COL
	# Explicitly don't import * from pageindex, make clear what we re-use
from zim.plugins.tags import *


def color_to_string(color):
	# helper method for comparing gtk.gdk.Color objects
	return '%i,%i,%i' % (color.red, color.green, color.blue)



class TestTaggedPageTreeStore(tests.TestCase):

	def setUp(self):
		self.storeclass = TaggedPageTreeStore
		self.viewclass = TaggedPageTreeView
		self.index = Index(dbfile=':memory:')
		self.notebook = tests.get_test_notebook()
		self.index.set_notebook(self.notebook)
		self.notebook.index.update()

	def runTest(self):
		'''Test TaggedPageTreeStore index interface'''
		# This is one big test instead of seperate sub tests because in the
		# subclass we generate a file based notebook in setUp, and we do not
		# want to do that many times.
		# Hooking up the treeview as well just to see if we get any errors
		# From the order the signals are generated.

		ui = MockUI()
		cloud = TagCloudWidget(ui)
		treeview = self.viewclass(ui, cloud)
		#~ treestore = TaggedPageTreeStore(self.index)
		#~ self.assertEqual(treestore.get_flags(), 0)
		#~ self.assertEqual(treestore.get_n_columns(), 5)
		#~ treeview.set_model(treestore)
		# FIXME prefer commented lines above
		cloud.do_set_notebook(ui, self.notebook)
		treeview.do_set_notebook(ui, self.notebook)
		treestore = treeview.get_model()
		if isinstance(treeview, TaggedPageTreeView):
			treestore = treestore.get_model() # look inside filtered model
		self.assertTrue(isinstance(treestore, self.storeclass))

		self.assertEqual(treestore.get_flags(), 0)
		self.assertEqual(treestore.get_n_columns(), 5)

		def process_events(*a):
			while gtk.events_pending():
				gtk.main_iteration(block=False)
			return True # continue

		self.index.update(callback=process_events)
		process_events()

		#~ treeview = PageTreeView(None) # just run hidden to check errors
		#~ treeview.set_model(treestore)

		n = treestore.on_iter_n_children(None)
		self.assertTrue(n > 0)
		n = treestore.iter_n_children(None)
		self.assertTrue(n > 0)

		for i in range(treestore.get_n_columns()):
			self.assertTrue(not treestore.get_column_type(i) is None)

		# Quick check for basic methods
		iter = treestore.on_get_iter((0,))
		self.assertTrue(isinstance(iter, (PageTreeIter, PageTreeTagIter)))
		if self.storeclass is TaggedPageTreeStore:
			self.assertTrue(isinstance(iter, PageTreeIter))
			self.assertTrue(isinstance(iter.indexpath, IndexPath))
			self.assertFalse(iter.indexpath.isroot)
		else:
			self.assertTrue(isinstance(iter, PageTreeTagIter))
			self.assertTrue(isinstance(iter.indextag, IndexTag))
		basename = treestore.on_get_value(iter, 0)
		self.assertTrue(len(basename) > 0)
		self.assertEqual(iter.treepath, (0,))
		self.assertEqual(treestore.on_get_path(iter), (0,))
		if self.storeclass is TaggedPageTreeStore:
			self.assertEqual(treestore.get_treepath(iter.indexpath), (0,))
			self.assertEqual(treestore.get_treepath(Path(iter.indexpath.name)), (0,))
		else:
			self.assertEqual(treestore.get_treepath(iter.indextag), (0,))

		iter2 = treestore.on_iter_children(None)
		if self.storeclass is TaggedPageTreeStore:
			self.assertEqual(iter2.indexpath, iter.indexpath)
		else:
			self.assertEqual(iter2.indextag, iter.indextag)

		self.assertTrue(treestore.on_get_iter((20,20,20,20,20)) is None)
		self.assertTrue(treestore.get_treepath(Path('nonexisting')) is None)
		self.assertRaises(ValueError, treestore.get_treepath, Path(':'))

		# Now walk through the whole tree testing the API
		nitems = 0
		path = (0,)
		prevpath = None
		while path:
			#~ print '>>', path
			assert path != prevpath, 'Prevent infinite loop'
			nitems += 1
			prevpath = path

			iter = treestore.get_iter(path)
			self.assertEqual(treestore.get_path(iter), tuple(path))

			if isinstance(treestore.on_get_iter(path), PageTreeIter):
				self._check_indexpath_iter(treestore, iter, path)
			else:
				self._check_indextag_iter(treestore, iter, path)

			# Determine how to continue
			if treestore.iter_has_child(iter):
				path = path + (0,)
			else:
				path = path[:-1] + (path[-1]+1,) # increase last member
				while path:
					try:
						treestore.get_iter(path)
					except ValueError:
						path = path[:-1]
						if len(path):
							path = path[:-1] + (path[-1]+1,) # increase last member
					else:
						break

		self.assertTrue(nitems > 10) # double check sanity of loop

		# Check if all the signals go OK
		treestore.disconnect()
		del treestore
		self.index.flush()
		treestore = self.storeclass(self.index, cloud)
		self.index.update(callback=process_events)
		#~ for page in reversed(list(self.notebook.walk())): # delete bottom up
			#~ self.notebook.delete_page(page)
			#~ process_events()

	def _check_indexpath_iter(self, treestore, iter, path):
		# checks specific for nodes that map to IndexPath object
		indexpath = treestore.get_indexpath(iter)
		self.assertTrue(path in treestore.get_treepaths(indexpath))

		page = self.notebook.get_page(indexpath)
		self.assertEqual(treestore.get_value(iter, NAME_COL), page.basename)
		self.assertEqual(treestore.get_value(iter, PATH_COL), page)
		if page.hascontent or page.haschildren:
			self.assertEqual(treestore.get_value(iter, EMPTY_COL), False)
			self.assertEqual(treestore.get_value(iter, STYLE_COL), pango.STYLE_NORMAL)
			self.assertEqual(
				color_to_string( treestore.get_value(iter, FGCOLOR_COL) ),
				color_to_string( treestore.NORMAL_COLOR) )
		else:
			self.assertEqual(treestore.get_value(iter, EMPTY_COL), True)
			self.assertEqual(treestore.get_value(iter, STYLE_COL), pango.STYLE_ITALIC)
			self.assertEqual(
				color_to_string( treestore.get_value(iter, FGCOLOR_COL) ),
				color_to_string( treestore.EMPTY_COLOR) )

		self._check_iter_children(treestore, iter, path, indexpath.haschildren)

	def _check_indextag_iter(self, treestore, iter, path):
		# checks specific for nodes that map to IndexTag object
		self.assertTrue(treestore.get_indexpath(iter) is None)

		indextag = treestore.get_indextag(iter)
		self.assertTrue(path in treestore.get_treepaths(indextag))

		self.assertEqual(treestore.get_value(iter, NAME_COL), indextag.name)
		self.assertEqual(treestore.get_value(iter, PATH_COL), indextag)
		if indextag == treestore.untagged:
			self.assertEqual(treestore.get_value(iter, EMPTY_COL), True)
			self.assertEqual(treestore.get_value(iter, STYLE_COL), pango.STYLE_ITALIC)
			self.assertEqual(
				color_to_string( treestore.get_value(iter, FGCOLOR_COL) ),
				color_to_string( treestore.EMPTY_COLOR) )
		else:
			self.assertEqual(treestore.get_value(iter, EMPTY_COL), False)
			self.assertEqual(treestore.get_value(iter, STYLE_COL), pango.STYLE_NORMAL)
			self.assertEqual(
				color_to_string( treestore.get_value(iter, FGCOLOR_COL) ),
				color_to_string( treestore.NORMAL_COLOR) )

		if indextag == treestore.untagged:
			haschildren = self.index.n_list_untagged() > 0
		else:
			haschildren = self.index.n_list_tagged(indextag) > 0
		self._check_iter_children(treestore, iter, path, haschildren)

	def _check_iter_children(self, treestore, iter, path, haschildren):
		# Check API for children is consistent
		if haschildren:
			self.assertTrue(treestore.iter_has_child(iter))
			child = treestore.iter_children(iter)
			self.assertTrue(not child is None)
			child = treestore.iter_nth_child(iter, 0)
			self.assertTrue(not child is None)
			parent = treestore.iter_parent(child)
			self.assertEqual(treestore.get_path(parent), path)
			childpath = treestore.get_path(child)
			self.assertEqual(
				childpath, tuple(path) + (0,))
			n = treestore.iter_n_children(iter)
			for i in range(1, n):
				child = treestore.iter_next(child)
				childpath = treestore.get_path(child)
				self.assertEqual(
					childpath, tuple(path) + (i,))
			child = treestore.iter_next(child)
			self.assertTrue(child is None)
		else:
			self.assertTrue(not treestore.iter_has_child(iter))
			child = treestore.iter_children(iter)
			self.assertTrue(child is None)
			child = treestore.iter_nth_child(iter, 0)
			self.assertTrue(child is None)


class TestTagsPageTreeStore(TestTaggedPageTreeStore):

	def setUp(self):
		TestTaggedPageTreeStore.setUp(self)
		self.storeclass = TagsPageTreeStore
		self.viewclass = TagsPageTreeView

	def runTest(self):
		'''Test TagsPageTreeStore index interface'''
		TestTaggedPageTreeStore.runTest(self)


class MockUI(tests.MockObject):

	page = None
	notebook = None
