# Copyright (c) Facebook, Inc. and its affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
#


import os

from .dataset import VQA2Dataset, VQAConcatDataset
from pythia.core.tasks.dataset_builder import DatasetBuilder
from pythia.core.registry import Registry


@Registry.register_builder('vqa2')
class VQA2Builder(DatasetBuilder):
    def __init__(self):
        super(VQA2Builder, self).__init__('VQA2')

    def _load(self, **opts):
        dataset_type = opts['dataset_type']

        self.data_root_dir = opts['data_root_dir']
        image_features = opts['image_feat_train'][0].split(',')
        self.num_image_features = len(image_features)

        dataset = None
        if dataset_type == 'train':
            dataset = self.prepare_train_data_set(**opts)
        elif dataset_type == 'dev':
            dataset = self.prepare_eval_data_set(**opts)
        elif dataset_type == 'test':
            dataset = self.prepare_test_data_set(**opts)
        else:
            raise NotImplementedError("Unknown dataset type: %s"
                                      % dataset_type)

        self.dataset = dataset
        self.dataset_class = VQA2Dataset
        return dataset

    def _build(self, **opts):
        # TODO: Build actually here
        return

    def update_config_for_model(self, config):
        config['num_vocab_txt'] = self.dataset.vocab_dict.num_vocab
        config['vocab_size'] = self.dataset.vocab_dict.num_vocab
        config['num_choices'] = self.dataset.answer_dict.num_vocab
        config['num_image_features'] = self.num_image_features

    def init_args(self, parser):
        parser.add_argument_group("VQA2 task specific arguments")
        parser.add_argument('--data_root_dir', type=str, default="../data",
                            help="Root directory for data")

    def prepare_train_data_set(self, **data_config):
        return self.prepare_data_set('imdb_file_train',
                                     'image_feat_train',
                                     **data_config)

    def prepare_eval_data_set(self, **data_config):
        # TODO: Add enforce_slow_reader to task args
        enforce_slow_reader = data_config['enforce_slow_reader']
        if enforce_slow_reader is True:
            data_config['image_fast_reader'] = False

        return self.prepare_data_set('imdb_file_val', 'image_feat_val',
                                     **data_config)

    def prepare_test_data_set(self, **data_config):
        data_config['image_fast_reader'] = False
        return self.prepare_data_set('imdb_file_test', 'image_feat_test',
                                     **data_config)

    def set_dataset_class(self, cls):
        self.dataset_class = cls

    def prepare_data_set(self, imdb_file_label,
                         image_dir_label, **data_config):
        # get the potential shared data_config info
        # TODO: Update this and move default stuff to configuration
        data_root_dir = data_config['data_root_dir']
        vocab_question_f = os.path.join(
            data_root_dir, data_config['vocab_question_file'])
        vocab_answer_file = os.path.join(
            data_root_dir, data_config['vocab_answer_file'])
        question_max_len = data_config.get('question_max_len', 26)

        layout_max_len = 0
        if 'vocab_layout_file' in data_config:
            layout_max_len = data_config.get('layout_max_len', 13)

        prune_filter_mod = data_config.get('prune_filter_module', False)
        image_depth_first = data_config['image_depth_first']
        image_fast_reader = data_config.get('image_fast_reader', False)
        verbose = data_config.get('verbose', False)
        test_mode = data_config.get('test_mode', False)

        imdb_files = data_config[imdb_file_label]
        image_feat_dirs = data_config[image_dir_label]
        assert len(imdb_files) == len(image_feat_dirs), \
            image_dir_label + "has different length with " + image_dir_label
        image_max_loc = data_config.get('image_max_loc', None)

        datasets = []
        dataset_type = data_config.get('dataset_type', "train")

        copy_included = data_config.get('copy_included', False)

        for imdb_file_trn_name, image_feat_dir in \
                zip(imdb_files, image_feat_dirs):
            imdb_file_trn = os.path.join(data_root_dir, imdb_file_trn_name)
            image_feat_dirs = [os.path.join(data_root_dir, d)
                               for d in image_feat_dir.split(',')]

            cls = self.dataset_class
            train_dataset = cls(imdb_file=imdb_file_trn,
                                image_feat_directories=image_feat_dirs,
                                T_encoder=question_max_len,
                                T_decoder=layout_max_len,
                                assembler=None,
                                vocab_question_file=vocab_question_f,
                                vocab_answer_file=vocab_answer_file,
                                prune_filter_module=prune_filter_mod,
                                image_depth_first=image_depth_first,
                                fast_read=image_fast_reader,
                                verbose=verbose,
                                test_mode=test_mode,
                                dataset_type=dataset_type,
                                copy_included=copy_included,
                                image_max_loc=image_max_loc)
            datasets.append(train_dataset)

        dataset = VQAConcatDataset(datasets)

        return dataset